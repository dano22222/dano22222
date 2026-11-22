"""hourly era5 reanalysis from the open-meteo historical weather api.

two ways of downloading are provided:
  download_region  the full experiment: every sampled location of a region
                   (1000 points), cached point by point so an interrupted run
                   can resume. used from the notebook and scripts/download_weather.py.
  download_sample  a small, quick regional sample (a few locations in one api
                   call), used live by the streamlit app.

open-meteo counts a request for more than 14 days, or more than 10 variables,
as several calls. a full year at one location is therefore about 26 call units,
and the free limit is 10 000 units per day. the 1000 point experiment must be
spread over several hours, while the app only asks for a handful of locations.
"""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import pandas as pd
import requests
from src.geography import ROOT

WEATHER_DIR = ROOT / 'data/weather'
URL = 'https://archive-api.open-meteo.com/v1/archive'

#the two variables needed by the analyses
CORE_VARIABLES = ['temperature_2m', 'precipitation']
#other relevant properties for reservoirs (rain vs snow, humidity, wind, clouds).
#eight variables in total stay below the 10 variable limit, so they cost no extra quota
VARIABLES = CORE_VARIABLES + ['rain', 'snowfall', 'relative_humidity_2m',
                              'wind_speed_10m', 'wind_gusts_10m', 'cloud_cover']
#units the api must return, checked so that silent unit changes are detected
UNITS = {'temperature_2m': '°C', 'precipitation': 'mm', 'rain': 'mm', 'snowfall': 'cm',
         'relative_humidity_2m': '%', 'wind_speed_10m': 'km/h', 'wind_gusts_10m': 'km/h',
         'cloud_cover': '%'}


class WeatherRateLimit(RuntimeError):
    """raised when open-meteo answers 429; stop and resume later instead of hammering the api."""


def expected_hours(start, end):
    """all hourly utc timestamps from start 00:00 to end 23:00 (8784 for the leap year 2024)."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start > end:
        raise ValueError('Start must not follow end.')
    return pd.date_range(start, end + pd.Timedelta(days=1), inclusive='left', freq='h', tz='UTC')


def estimate_download(start, end, points=1000, variables=CORE_VARIABLES):
    """rough size and quota estimate before a download is started."""
    hours = len(expected_hours(start, end))
    days = hours / 24
    values = points * hours * len(variables)
    #open meteo weighting: one unit per 14 days and per 10 variables, at least one
    units_per_point = max(1, days / 14) * max(1, len(variables) / 10)
    return {'points': points, 'hours_per_point': hours, 'variables': len(variables),
            'values': values, 'float32_MB': round(values * 4 / 1e6, 2),
            'estimated_api_call_units': round(points * units_per_point, 1)}


def validate_hourly(df, start, end, variables=None):
    """reject incomplete, duplicated, missing or physically impossible weather data."""
    variables = list(df.columns) if variables is None else list(variables)
    if not df.index.equals(expected_hours(start, end)):
        raise ValueError('Incomplete/duplicate/unexpected hourly timestamps.')
    if not set(variables).issubset(df.columns):
        raise ValueError('Missing weather variables.')
    if not np.isfinite(df[variables].to_numpy(dtype=float)).all():
        raise ValueError('Missing or nonfinite weather.')
    for column in ['precipitation', 'rain', 'snowfall']:
        if column in variables and (df[column] < 0).any():
            raise ValueError(f'Negative {column}.')
    return df


def _get(params, session):
    """one api request with retries for temporary server errors."""
    response = None
    for attempt in range(4):
        response = session.get(URL, params=params, timeout=120)
        if response.status_code == 429:
            #quota reached: never retry in a loop, report it to the caller
            try:
                reason = response.json().get('reason', 'quota reached')
            except ValueError:
                reason = 'quota reached'
            raise WeatherRateLimit(f'Open-Meteo: {reason}. Cached points are safe; resume later.')
        if response.status_code >= 500 and attempt < 3:
            #temporary server problem: wait 1, 2, 4 seconds and try again
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        break
    return response.json()


def _parse(payload, start, end, variables):
    """turn one location of an api response into a validated hourly dataframe."""
    if payload.get('error'):
        raise ValueError(payload.get('reason', 'Open-Meteo error'))
    units = payload.get('hourly_units', {})
    for variable in variables:
        if units.get(variable) != UNITS[variable]:
            raise ValueError(f'Unexpected unit for {variable}: {units.get(variable)}')
    df = pd.DataFrame(payload['hourly']).rename(columns={'time': 'timestamp'})
    df['timestamp'] = pd.to_datetime(df.timestamp, utc=True)
    df = df.set_index('timestamp')[list(variables)].astype('float32')
    validate_hourly(df, start, end, variables)
    #keep the grid cell actually used by the api, which may differ from the requested point
    metadata = {k: payload.get(k) for k in ['latitude', 'longitude', 'elevation', 'timezone', 'hourly_units']}
    return df, metadata


def download_points(latitudes, longitudes, start, end, variables=VARIABLES, session=None):
    """download several locations in one request (open-meteo accepts comma separated lists)."""
    session = session or requests.Session()
    params = {'latitude': ','.join(f'{float(v):.6f}' for v in latitudes),
              'longitude': ','.join(f'{float(v):.6f}' for v in longitudes),
              'start_date': str(start), 'end_date': str(end), 'hourly': ','.join(variables),
              #era5 is selected explicitly, utc avoids daylight saving gaps,
              #land makes the api prefer a land grid cell near the coast
              'models': 'era5', 'timezone': 'UTC', 'cell_selection': 'land'}
    payload = _get(params, session)
    #one location gives a single object, several locations give a list
    payloads = payload if isinstance(payload, list) else [payload]
    if len(payloads) != len(latitudes):
        raise ValueError('Open-Meteo returned an unexpected number of locations.')
    return [_parse(p, start, end, variables) for p in payloads]


def download_point(latitude, longitude, start, end, session=None, variables=VARIABLES):
    """download one location; returns (hourly dataframe, metadata)."""
    return download_points([latitude], [longitude], start, end, variables, session)[0]


def load_points(region):
    """the fixed random sample of locations for one region, ordered by point id."""
    points = pd.read_parquet(ROOT / 'data/regions/points.parquet')
    points = points.loc[points.region == region].sort_values('point_id')
    if points.empty:
        raise ValueError(f'Unknown region {region}')
    return points


def coordinates_fingerprint(points):
    """short hash of point ids and coordinates, used to name the cache folder."""
    text = '\n'.join(f'{row.point_id},{row.latitude:.8f},{row.longitude:.8f}' for row in points.itertuples())
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def download_region(region, start, end, approved=False, max_points=None, delay=2.5, variables=VARIABLES):
    """download all sampled locations of a region and return their hourly mean.

    region is a key such as NO3, start and end are dates (yyyy-mm-dd). the
    coordinates are looked up in data/regions/points.parquet. every point is saved
    as its own parquet file, so a run stopped by the api quota can be resumed
    and already downloaded points are reused. the mean is saved to
    data/weather/<region>_<start>_<end>_mean.parquet when all 1000 points are present.
    """
    points = load_points(region)
    if max_points is not None:
        points = points.head(max_points)
    if len(points) > 1 and not approved:
        raise PermissionError('Bulk weather download requires explicit approval.')
    #the cache folder name includes a fingerprint of the coordinates, so a new sample never reuses old files.
    #explicit number formatting keeps the fingerprint identical across pandas versions
    fingerprint = coordinates_fingerprint(points)
    folder = WEATHER_DIR / f'{region}_{start}_{end}_{fingerprint}'
    folder.mkdir(parents=True, exist_ok=True)
    total = np.zeros((len(expected_hours(start, end)), len(variables)), dtype='float64')
    session = requests.Session()
    downloaded = 0
    for row in points.itertuples():
        path = folder / f'point_{row.point_id:04d}.parquet'
        cached = pd.read_parquet(path) if path.exists() else None
        if cached is not None and set(variables).issubset(cached.columns):
            #reuse the cached point when it already contains every requested variable
            df = validate_hourly(cached, start, end, variables)
        else:
            df, metadata = download_point(row.latitude, row.longitude, start, end, session, variables=variables)
            #write to a temporary file first, so an interruption never leaves a broken parquet file
            temporary = path.with_suffix('.tmp')
            df.to_parquet(temporary)
            temporary.replace(path)
            (folder / f'point_{row.point_id:04d}.json').write_text(json.dumps({
                'requested_latitude': row.latitude, 'requested_longitude': row.longitude,
                'source': URL, 'model': 'era5', **metadata}, indent=2))
            downloaded += 1
            if downloaded % 10 == 0:
                print(f'{region}: {downloaded} new points; current ID {row.point_id}', flush=True)
            #pause between requests to stay within the per minute limit
            time.sleep(delay)
        total += df[variables].to_numpy()
    #spatial mean over all locations, hour by hour
    result = pd.DataFrame(total / len(points), index=expected_hours(start, end), columns=variables)
    result.index.name = 'timestamp'
    if len(points) == 1000:
        target = WEATHER_DIR / f'{region}_{start}_{end}_mean.parquet'
        result.to_parquet(target)
        target.with_suffix('.json').write_text(json.dumps({
            'region': region, 'start': start, 'end': end, 'points': len(points), 'complete_1000': True,
            'variables': variables, 'model': 'era5', 'timezone': 'UTC', 'coordinates_hash': fingerprint,
            'source': URL, 'point_cache': folder.name}, indent=2))
    return result


def load_region(region, start='2024-01-01', end='2024-12-31'):
    """read a saved 1000 point regional mean and its metadata."""
    path = WEATHER_DIR / f'{region}_{start}_{end}_mean.parquet'
    metadata = json.loads(path.with_suffix('.json').read_text())
    if not metadata['complete_1000']:
        raise ValueError('Incomplete regional mean.')
    return validate_hourly(pd.read_parquet(path), start, end), metadata


def download_sample(region, start, end, n_points=100, variables=VARIABLES, session=None,
                    progress=None, pause=time.sleep):
    """quick regional estimate: the mean of the first n_points sampled locations.

    the points in points.parquet are already in random order, so the first n
    points are a random subset of the region. the default is 100 locations
    (part 3 feedback); they are fetched in a few batched api requests, which
    takes some minutes for a full year because of the open meteo limit per
    minute. progress is an optional callback with the share downloaded.
    returns (hourly mean dataframe, metadata).
    """
    points = load_points(region).head(int(n_points))
    session = session or requests.Session()
    #one location costs about 26 call units per year (8 variables); the locations are sent
    #in batches that stay below the open meteo limit per minute, with a pause in between
    days = len(expected_hours(start, end)) / 24
    units = max(1, days / 14) * max(1, len(variables) / 10)
    batch = max(1, int(UNITS_PER_MINUTE // units))
    results = []
    for first in range(0, len(points), batch):
        if first:
            pause(61)
        part = points.iloc[first:first + batch]
        results.extend(download_points(part.latitude, part.longitude, start, end, variables, session))
        if progress:
            progress(min(1., (first + len(part)) / len(points)))
    frames = [df for df, _ in results]
    mean = sum(frame.astype('float64') for frame in frames) / len(frames)
    mean.index.name = 'timestamp'
    metadata = {'region': region, 'start': start, 'end': end, 'points': len(points),
                'variables': list(variables), 'model': 'era5', 'timezone': 'UTC', 'source': URL,
                'locations': points[['point_id', 'latitude', 'longitude']].to_dict('records'),
                'grid_cells': [{'latitude': m['latitude'], 'longitude': m['longitude'],
                                'elevation': m['elevation']} for _, m in results]}
    return mean, metadata


#daily aggregates for part 4 (map, sliding window correlation and forecasting).
#daily data are much smaller than hourly data for multi year periods, and the
#days are cut in norwegian local time (europe/oslo), the same calendar as the
#weekly nve reservoir statistics
DAILY_VARIABLES = ['temperature_2m_mean', 'precipitation_sum', 'rain_sum', 'snowfall_sum', 'wind_speed_10m_max']
DAILY_UNITS = {'temperature_2m_mean': '°C', 'precipitation_sum': 'mm', 'rain_sum': 'mm',
               'snowfall_sum': 'cm', 'wind_speed_10m_max': 'km/h'}
#how each daily variable is aggregated to weeks (sums for amounts, means for states)
WEEKLY_AGGREGATION = {'temperature_2m_mean': 'mean', 'precipitation_sum': 'sum', 'rain_sum': 'sum',
                      'snowfall_sum': 'sum', 'wind_speed_10m_max': 'mean'}
#readable names used in the app and in plots
WEATHER_LABELS = {'temperature_2m_mean': 'Temperature (°C)', 'precipitation_sum': 'Precipitation (mm)',
                  'rain_sum': 'Rain (mm)', 'snowfall_sum': 'Snowfall (cm)',
                  'wind_speed_10m_max': 'Daily max wind speed (km/h)'}
#hourly variable that matches each daily variable (for the hourly spc and lof analyses)
HOURLY_EQUIVALENT = {'temperature_2m_mean': 'temperature_2m', 'precipitation_sum': 'precipitation',
                     'rain_sum': 'rain', 'snowfall_sum': 'snowfall', 'wind_speed_10m_max': 'wind_speed_10m'}
HOURLY_LABELS = {'temperature_2m': 'Temperature (°C)', 'precipitation': 'Precipitation (mm per hour)',
                 'rain': 'Rain (mm per hour)', 'snowfall': 'Snowfall (cm per hour)',
                 'relative_humidity_2m': 'Relative humidity (%)', 'wind_speed_10m': 'Wind speed (km/h)',
                 'wind_gusts_10m': 'Wind gusts (km/h)', 'cloud_cover': 'Cloud cover (%)'}


def latest_era5_date():
    """era5 is published with about five days delay; later days are not requested."""
    return (pd.Timestamp.now(tz='Europe/Oslo') - pd.Timedelta(days=6)).normalize().tz_localize(None)


def _parse_daily(payload, variables):
    """turn one location of a daily api response into a dataframe indexed by local date."""
    if payload.get('error'):
        raise ValueError(payload.get('reason', 'Open-Meteo error'))
    units = payload.get('daily_units', {})
    for variable in variables:
        if units.get(variable) != DAILY_UNITS[variable]:
            raise ValueError(f'Unexpected unit for {variable}: {units.get(variable)}')
    df = pd.DataFrame(payload['daily']).rename(columns={'time': 'date'})
    df['date'] = pd.to_datetime(df.date)
    #missing values arrive as null; they stay nan and are handled by the weekly aggregation
    return df.set_index('date')[list(variables)].apply(pd.to_numeric, errors='coerce').astype('float64')


def download_daily(latitudes, longitudes, start, end, variables=DAILY_VARIABLES, session=None):
    """daily era5 aggregates for several locations in one request (days in europe/oslo time)."""
    if pd.Timestamp(start) > pd.Timestamp(end):
        raise ValueError('Start must not follow end.')
    session = session or requests.Session()
    params = {'latitude': ','.join(f'{float(v):.6f}' for v in latitudes),
              'longitude': ','.join(f'{float(v):.6f}' for v in longitudes),
              'start_date': str(pd.Timestamp(start).date()), 'end_date': str(pd.Timestamp(end).date()),
              'daily': ','.join(variables), 'models': 'era5', 'timezone': 'Europe/Oslo',
              'cell_selection': 'land'}
    payload = _get(params, session)
    payloads = payload if isinstance(payload, list) else [payload]
    if len(payloads) != len(latitudes):
        raise ValueError('Open-Meteo returned an unexpected number of locations.')
    return [_parse_daily(p, variables) for p in payloads]


#open meteo also limits the call units per minute (600 on the free plan); long periods are
#therefore downloaded in pieces of one year, with pauses that keep below this limit
UNITS_PER_MINUTE = 500


def _daily_in_chunks(latitudes, longitudes, start, end, variables, session, pause=time.sleep):
    """download a long period year by year, waiting when the per minute quota would be exceeded."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    pieces, used, window_start = [], 0., time.monotonic()
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + pd.DateOffset(years=1) - pd.Timedelta(days=1), end)
        days = (chunk_end - chunk_start).days + 1
        units = len(latitudes) * max(1, days / 14) * max(1, len(variables) / 10)
        if used + units > UNITS_PER_MINUTE:
            #wait until a new minute window starts before the next request
            pause(max(0., 61 - (time.monotonic() - window_start)))
            used, window_start = 0., time.monotonic()
        try:
            frames = download_daily(latitudes, longitudes, chunk_start, chunk_end, variables, session)
        except WeatherRateLimit as error:
            #the daily or hourly quota cannot be waited out here; only the minute limit is retried once
            if 'Minutely' not in str(error):
                raise
            pause(61)
            used, window_start = 0., time.monotonic()
            frames = download_daily(latitudes, longitudes, chunk_start, chunk_end, variables, session)
        used += units
        pieces.append(frames)
        chunk_start = chunk_end + pd.Timedelta(days=1)
    return [pd.concat([piece[i] for piece in pieces]) for i in range(len(latitudes))]


def download_daily_regions(regions, start, end, n_points=3, variables=DAILY_VARIABLES, session=None):
    """regional daily means for several regions, with all locations in each request.

    the first n_points sampled locations of every region are requested together
    and averaged per region; periods longer than a year are split into yearly
    requests. returns a dict {region: daily dataframe}.
    """
    points = pd.concat([load_points(r).head(int(n_points)) for r in regions], ignore_index=True)
    session = session or requests.Session()
    frames = _daily_in_chunks(points.latitude.tolist(), points.longitude.tolist(), start, end, variables, session)
    result = {}
    for region in regions:
        selected = [f for f, r in zip(frames, points.region) if r == region]
        #mean over the locations, ignoring a missing value at a single location
        result[region] = pd.concat(selected).groupby(level=0).mean()
    return result


def download_daily_sample(region, start, end, n_points=3, variables=DAILY_VARIABLES, session=None):
    """daily mean of the first n_points sampled locations of one region."""
    return download_daily_regions([region], start, end, n_points, variables, session)[region]


def weekly_weather(daily, min_days=7):
    """aggregate daily weather to weeks ending on sunday (the nve reservoir weeks).

    amounts (precipitation, rain, snow) are summed and states (temperature,
    wind) are averaged. weeks with fewer than min_days valid days become nan
    instead of being based on part of a week.
    """
    rules = {c: WEEKLY_AGGREGATION.get(c, 'mean') for c in daily.columns}
    weekly = daily.resample('W-SUN').agg(rules)
    counts = daily.resample('W-SUN').count()
    return weekly.where(counts >= min_days)


ELEVATION_URL = 'https://api.open-meteo.com/v1/elevation'


def elevation(latitude, longitude, session=None):
    """terrain height in metres above sea level (copernicus dem 90 m) from the open-meteo elevation api."""
    session = session or requests.Session()
    response = session.get(ELEVATION_URL, params={'latitude': f'{float(latitude):.5f}',
                                                  'longitude': f'{float(longitude):.5f}'}, timeout=20)
    response.raise_for_status()
    values = response.json().get('elevation') or []
    if not values or values[0] is None:
        raise ValueError('No elevation returned for this point.')
    return float(values[0])
