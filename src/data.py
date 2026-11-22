"""cached data access for the streamlit pages (apis and mongodb).

every loader is wrapped in st.cache_data, so a page switch or a widget change
never downloads the same data twice. the caches are shared by all pages:
the map, the correlation page and the forecast page reuse the same weather
downloads when they ask for the same region and period. errors are raised to
the pages, which show a readable message instead of crashing.
"""
import os
import certifi
import pandas as pd
import pymongo
import streamlit as st
from dotenv import load_dotenv
from src import weather as meteo
from src.currency import fetch_exchange_rates


@st.cache_data(ttl=None, max_entries=64, show_spinner=False)
def daily_weather(region, start, end, n_points=3):
    """daily era5 regional mean (days in europe/oslo time) for one region and period."""
    return meteo.download_daily_sample(region, start, end, n_points)


@st.cache_data(ttl=None, max_entries=64, show_spinner=False)
def daily_weather_regions(regions, start, end, n_points=3):
    """daily era5 means for several regions in one api request (used by the map)."""
    return meteo.download_daily_regions(list(regions), start, end, n_points)


@st.cache_data(ttl=None, max_entries=64, show_spinner=False)
def weekly_weather(region, start, end, n_points=3):
    """weekly weather (nve weeks ending on sunday) for one region."""
    return meteo.weekly_weather(daily_weather(region, start, end, n_points))


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def exchange_rates(start, end):
    """daily eur and usd rates from norges bank (refreshed every six hours)."""
    return fetch_exchange_rates(start, end)


@st.cache_resource(show_spinner=False)
def mongo_collection():
    """connection to the mongodb atlas collection with the part 2 electricity flows."""
    load_dotenv()
    uri = os.getenv('MONGODB_URI')
    if not uri:
        try:
            uri = st.secrets['MONGODB_URI']
        except (KeyError, FileNotFoundError):
            raise RuntimeError('MongoDB credentials are missing (MONGODB_URI).')
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000, tlsCAFile=certifi.where())
    client.admin.command('ping')
    return client['ind320']['cross_border_flows']


@st.cache_data(ttl=3600, show_spinner=False)
def weekly_net_export(connection='NO2-DK1'):
    """weekly net export (export minus import, mwh) for one connection, in nve weeks.

    the timestamps are stored in utc in mongodb; the daily sums are made by
    the database in europe/oslo time so the weeks match the reservoir statistics.
    """
    pipeline = [
        {'$match': {'connection': connection}},
        {'$group': {'_id': {'day': {'$dateTrunc': {'date': '$timestamp', 'unit': 'day', 'timezone': 'Europe/Oslo'}},
                            'direction': '$direction'},
                    'energy_mwh': {'$sum': '$energy_mwh'}}},
    ]
    rows = [{'day': r['_id']['day'], 'direction': r['_id']['direction'], 'energy_mwh': r['energy_mwh']}
            for r in mongo_collection().aggregate(pipeline)]
    if not rows:
        raise ValueError(f'No electricity data for {connection}.')
    daily = pd.DataFrame(rows)
    #the day starts at oslo midnight; convert back to a plain local date
    daily['day'] = pd.to_datetime(daily['day'], utc=True).dt.tz_convert('Europe/Oslo').dt.tz_localize(None).dt.normalize()
    table = daily.pivot_table(index='day', columns='direction', values='energy_mwh', aggfunc='sum').fillna(0)
    exports = table[[c for c in table.columns if c.lower().startswith('export')]].sum(axis=1)
    imports = table[[c for c in table.columns if c.lower().startswith('import')]].sum(axis=1)
    weekly = (exports - imports).resample('W-SUN').sum(min_count=7)
    return weekly.rename('net_export_mwh').to_frame()
