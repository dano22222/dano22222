"""Streamlit runtime tests use a deterministic NVE fixture, no database writes."""
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]

def reservoir_fixture():
    #include all columns read by the existing app and several areas/years.
    df=pd.read_parquet(ROOT/'data/reservoir.parquet')
    return df.rename(columns={'kapasitet_TWh':'capacity_TWh','fylling_TWh':'stored_energy_TWh',
      'fyllingsgrad_forrige_uke':'fill_level_previous_week','endring_fyllingsgrad':'change_in_fill_level'})

def run_page(name):
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app=AppTest.from_file(str(ROOT/'pages'/name),default_timeout=60).run()
    assert not app.exception
    return app

def test_data_date_filters_table_and_export():
    app=run_page('2_Data.py')
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app.date_input[0].set_value((pd.Timestamp('2024-01-01').date(),pd.Timestamp('2024-01-31').date())).run()
    assert not app.exception
    displayed=app.dataframe[1].value
    assert len(displayed)>0 and displayed.date.min()>=pd.Timestamp('2024-01-01')
    assert displayed.date.max()<pd.Timestamp('2024-02-01')
    assert len(app.dataframe[0].value.iloc[0].fill_level)<=5

def test_plot_default_and_comparison():
    app=run_page('3_Plot.py')
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app.checkbox[0].check().run()
    assert not app.exception

def test_seasonality_tabs():
    app=run_page('5_Seasonality.py')
    assert len(app.tabs)==2

def test_weather_missing_then_pilot():
    app=run_page('6_Weather.py')
    assert not app.exception
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app.radio(key='weather_mode').set_value('Single-point pilot (not regional mean)').run()
    assert not app.exception and len(app.tabs)==2

def test_home():
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
    assert not app.exception
