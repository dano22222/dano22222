"""Resumable ERA5 retrieval: bounded memory, explicit approval for bulk downloads."""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import pandas as pd
import requests
from src.geography import ROOT
WEATHER_DIR=ROOT/'data/weather'
URL='https://archive-api.open-meteo.com/v1/archive'
VARIABLES=['temperature_2m','precipitation']

class WeatherRateLimit(RuntimeError):
    """Stop and resume later; never silently bypass the provider's quota."""

def expected_hours(start,end):
    start=pd.Timestamp(start);end=pd.Timestamp(end)
    if start> end:raise ValueError('Start must not follow end.')
    return pd.date_range(start,end+pd.Timedelta(days=1),inclusive='left',freq='h',tz='UTC')

def estimate_download(start,end,points=1000):
    hours=len(expected_hours(start,end));values=points*hours*len(VARIABLES)
    return {'points':points,'hours_per_point':hours,'point_hours':points*hours,
            'values':values,'float32_MB':round(values*4/1e6,2),
            'estimated_transfer_MB':[round(values*12/1e6),round(values*40/1e6)],
            'estimated_api_call_units':round(points*max(1,hours/24/14)*max(1,len(VARIABLES)/10),1)}

def validate_hourly(df,start,end):
    expected=expected_hours(start,end)
    if not df.index.equals(expected):raise ValueError('Incomplete/duplicate/unexpected hourly timestamps.')
    if not np.isfinite(df[VARIABLES].to_numpy()).all():raise ValueError('Missing or nonfinite weather.')
    if (df.precipitation<0).any():raise ValueError('Negative precipitation.')
    return df

def download_point(latitude,longitude,start,end,session=None):
    session=session or requests.Session()
    response=None
    for attempt in range(4):
        response=session.get(URL,params={'latitude':float(latitude),'longitude':float(longitude),
            'start_date':str(start),'end_date':str(end),'hourly':','.join(VARIABLES),
            'models':'era5','timezone':'UTC','cell_selection':'land'},timeout=120)
        if response.status_code==429:
            raise WeatherRateLimit('Open-Meteo quota reached. Cached points are safe; resume later.')
        if response.status_code>=500 and attempt<3:
            time.sleep(2**attempt);continue
        response.raise_for_status();break
    payload=response.json()
    if payload.get('error'):raise ValueError(payload.get('reason','Open-Meteo error'))
    if payload.get('hourly_units',{}).get('temperature_2m')!='°C' or payload.get('hourly_units',{}).get('precipitation')!='mm':
        raise ValueError('Unexpected weather units.')
    df=pd.DataFrame(payload['hourly']).rename(columns={'time':'timestamp'})
    df['timestamp']=pd.to_datetime(df.timestamp,utc=True)
    df=df.set_index('timestamp')[VARIABLES].astype('float32')
    validate_hourly(df,start,end)
    return df, {k:payload.get(k) for k in ['latitude','longitude','elevation','timezone','hourly_units']}

def download_region(region,start,end,approved=False,max_points=None,delay=2.5):
    """Lookup fixed coordinates, cache each point, and publish mean only if complete.

    Year-long calls have weighted quota units. Stop on 429; reuse cached files
    on the next invocation. Never round/deduplicate coordinates: elevation
    adjustment and nearest-grid selection can differ between sampled points.
    """
    points=pd.read_csv(ROOT/'data/regions/points.csv')
    points=points.loc[points.region==region].sort_values('point_id')
    if points.empty:raise ValueError(f'Unknown region {region}')
    if max_points is not None:points=points.head(max_points)
    if len(points)>1 and not approved:raise PermissionError('Bulk weather download requires explicit approval.')
    fingerprint=hashlib.sha256(points.to_csv(index=False).encode()).hexdigest()[:12]
    folder=WEATHER_DIR/f'{region}_{start}_{end}_{fingerprint}'
    folder.mkdir(parents=True,exist_ok=True)
    total=np.zeros((len(expected_hours(start,end)),2),dtype='float64')
    session=requests.Session();downloaded=0
    for row in points.itertuples():
        path=folder/f'point_{row.point_id:04d}.parquet'
        if path.exists():
            df=validate_hourly(pd.read_parquet(path),start,end)
        else:
            df,metadata=download_point(row.latitude,row.longitude,start,end,session)
            temporary=path.with_suffix('.tmp');df.to_parquet(temporary);temporary.replace(path)
            (folder/f'point_{row.point_id:04d}.json').write_text(json.dumps({
                'requested_latitude':row.latitude,'requested_longitude':row.longitude,
                'source':URL,'model':'era5',**metadata},indent=2))
            downloaded+=1
            if downloaded%10==0:print(f'{region}: {downloaded} new points; current ID {row.point_id}',flush=True)
            time.sleep(delay)
        total+=df[VARIABLES].to_numpy()
    result=pd.DataFrame(total/len(points),index=expected_hours(start,end),columns=VARIABLES)
    result.index.name='timestamp'
    label='mean' if len(points)==1000 else f'pilot_{len(points)}'
    target=WEATHER_DIR/f'{region}_{start}_{end}_{label}.parquet'
    result.to_parquet(target)
    target.with_suffix('.json').write_text(json.dumps({'region':region,'start':start,'end':end,
        'points':len(points),'complete_1000':len(points)==1000,'model':'era5','timezone':'UTC',
        'coordinates_hash':fingerprint,'source':URL,'point_cache':folder.name},indent=2))
    return result

def load_region(region,start='2024-01-01',end='2024-12-31',pilot=False):
    suffix='pilot_1' if pilot else 'mean'
    path=WEATHER_DIR/f'{region}_{start}_{end}_{suffix}.parquet'
    metadata=json.loads(path.with_suffix('.json').read_text())
    if not pilot and not metadata['complete_1000']:raise ValueError('Incomplete regional mean.')
    return validate_hourly(pd.read_parquet(path),start,end),metadata
