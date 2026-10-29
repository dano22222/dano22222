"""nve reservoir statistics without streamlit, used by the notebook and the analyses."""
from pathlib import Path
import pandas as pd
import requests

#official nve magasinstatistikk api (same source as nve_api.py in the app)
URL = 'https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData'
ROOT = Path(__file__).resolve().parents[1]


def fetch_reservoir():
    """download all reservoir statistics and give the key columns english names."""
    response = requests.get(URL, timeout=90)
    response.raise_for_status()
    df = pd.DataFrame(response.json()).rename(columns={
        'dato_Id': 'date', 'omrType': 'area_type', 'omrnr': 'area',
        'fyllingsgrad': 'fill_level', 'iso_aar': 'year', 'iso_uke': 'week'})
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values(['area_type', 'area', 'date'])


def weekly_series(df, area_type='EL', area=3):
    """weekly filling fraction for one area, for example EL 3 (= NO3).

    one area is used, never an average of overlapping areas. missing weeks
    raise an error instead of being interpolated, because stl and the
    spectrogram need a complete, regular series.
    """
    s = df.loc[(df.area_type == area_type) & (df.area == area)].set_index('date').fill_level.sort_index()
    if s.empty or s.index.has_duplicates:
        raise ValueError('Missing or duplicate reservoir series.')
    #compare with a complete weekly calendar to detect gaps
    expected = pd.date_range(s.index.min(), s.index.max(), freq='7D')
    s = s.reindex(expected)
    if s.isna().any():
        raise ValueError('Missing weeks: inspect source data before decomposition.')
    return s


def filter_dates(df, start, end):
    """rows between two calendar dates, both included (all of the last day is kept)."""
    dates = pd.to_datetime(df['date'])
    return df.loc[(dates >= pd.Timestamp(start)) & (dates < pd.Timestamp(end) + pd.Timedelta(days=1))].copy()
