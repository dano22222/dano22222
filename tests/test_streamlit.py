"""streamlit runtime tests use a deterministic nve fixture, no database writes."""
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

def fake_sample(region,start,end,n_points=5,**kwargs):
    #synthetic hourly weather instead of a network request
    import numpy as np
    from src.weather import VARIABLES,expected_hours
    index=expected_hours(start,end);rng=np.random.default_rng(len(region))
    df=pd.DataFrame({v:rng.gamma(1.,1.,len(index)) for v in VARIABLES},index=index)
    df['temperature_2m']=rng.normal(5,8,len(index))
    return df,{'region':region,'points':n_points,'locations':[{'point_id':0,'latitude':63.,'longitude':10.}]}

def test_weather_follows_area_selector_and_downloads_live():
    with patch('src.weather.download_sample',side_effect=fake_sample) as download:
        app=run_page('6_Weather.py')
        assert len(app.tabs)==2
        assert download.call_args.args[:2]==('NO3','2024-01-01')
        #changing the shared selector to vass 3 downloads the northern region instead
        with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
            app.radio(key='shared_type').set_value('VASS').run()
            app.selectbox(key='shared_area').set_value(3).run()
        assert not app.exception and download.call_args.args[0]=='VASS3'

def test_weather_complete_mean_option():
    with patch('src.weather.download_sample',side_effect=fake_sample):
        app=run_page('6_Weather.py')
        with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
            app.checkbox[0].check().run()
    assert not app.exception and len(app.tabs)==2

def test_home():
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
    assert not app.exception


def test_area_selection_persists_between_pages():
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        app.switch_page('pages/2_Data.py').run()
        app.selectbox(key='shared_area').set_value(2).run()
        assert app.session_state['reservoir_selection']==('EL',2)
        app.switch_page('pages/5_Seasonality.py').run()
        assert not app.exception
        assert app.selectbox(key='shared_area').value==2
        app.radio(key='shared_type').set_value('NO').run()
        assert not app.exception
        assert app.session_state['reservoir_selection']==('NO',0)


def test_existing_electricity_page_with_database_fixture():
    import os
    from unittest.mock import MagicMock
    times=pd.date_range('2025-01-01',periods=48,freq='h')
    records=[{'connection':'NO2-DK1','direction':direction,'timestamp':t,
              'year':2025,'month':1,'power_mw':100.,'energy_mwh':100.}
             for t in times for direction in ['Export NO2 to DK1','Import DK1 to NO2']]
    collection=MagicMock()
    collection.distinct.side_effect=lambda field,*args: ['NO2-DK1'] if field=='connection' else [2025]
    collection.find.return_value=records
    client=MagicMock();client.__getitem__.return_value.__getitem__.return_value=collection
    with patch.dict(os.environ,{'MONGODB_URI':'mongodb://localhost'}),patch('pymongo.MongoClient',return_value=client):
        app=AppTest.from_file(str(ROOT/'pages/4_Electricity.py'),default_timeout=60).run()
    assert not app.exception
    assert len(app.selectbox)==1 and len(getattr(app,'pills',app.get('button_group')))==1
