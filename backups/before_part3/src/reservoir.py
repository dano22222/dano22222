"""NVE reservoir preparation independent of Streamlit."""
from pathlib import Path
import pandas as pd
import requests
URL='https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData'
ROOT=Path(__file__).resolve().parents[1]

def fetch_reservoir():
    response=requests.get(URL,timeout=90);response.raise_for_status()
    df=pd.DataFrame(response.json()).rename(columns={'dato_Id':'date','omrType':'area_type',
        'omrnr':'area','fyllingsgrad':'fill_level','iso_aar':'year','iso_uke':'week'})
    df['date']=pd.to_datetime(df['date'])
    return df.sort_values(['area_type','area','date'])

def weekly_series(df, area_type='EL', area=3):
    """Use one region; reject missing weeks instead of hiding gaps by interpolation."""
    s=df.loc[(df.area_type==area_type)&(df.area==area)].set_index('date').fill_level.sort_index()
    if s.empty or s.index.has_duplicates:raise ValueError('Missing or duplicate reservoir series.')
    expected=pd.date_range(s.index.min(),s.index.max(),freq='7D')
    s=s.reindex(expected)
    if s.isna().any():raise ValueError('Missing weeks: inspect source data before decomposition.')
    return s

def filter_dates(df,start,end):
    """Inclusive calendar dates, including all observations on the final day."""
    dates=pd.to_datetime(df['date'])
    return df.loc[(dates>=pd.Timestamp(start)) & (dates<pd.Timestamp(end)+pd.Timedelta(days=1))].copy()
