"""streamlit runtime tests use a deterministic nve fixture, no database writes."""
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]


def fake_daily(latitudes,longitudes,start,end,variables=None,session=None):
    #synthetic daily era5 values for every requested location instead of a network request
    from src.weather import DAILY_VARIABLES
    days=pd.date_range(start,end,freq='D');rng=np.random.default_rng(len(days))
    frames=[]
    for _ in range(len(latitudes)):
        df=pd.DataFrame({v:rng.gamma(1.,2.,len(days)) for v in variables or DAILY_VARIABLES},index=days)
        if 'temperature_2m_mean' in df:
            df['temperature_2m_mean']=5+10*np.sin(2*np.pi*days.day_of_year.to_numpy()/365.25)
        frames.append(df)
    return frames


def fake_rates(start,end,*args,**kwargs):
    #synthetic business day exchange rates
    days=pd.bdate_range(start,end)
    return pd.DataFrame({'EUR':np.linspace(11,12,len(days)),'USD':np.linspace(10,11,len(days))},index=days)


@pytest.fixture(autouse=True)
def no_network():
    #every page test runs without internet access
    with patch('src.weather.download_daily',side_effect=fake_daily),\
         patch('src.data.fetch_exchange_rates',side_effect=fake_rates),\
         patch('src.weather.elevation',return_value=123.):
        yield

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


def test_data_overview_has_exchange_rate_tab():
    app=run_page('2_Data.py')
    assert len(app.tabs)==3 and len(app.metric)==2


def test_map_page_filling_and_weather_colouring():
    app=run_page('7_Map.py')
    assert 'time_frame' in app.session_state
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app.radio(key='map_colour').set_value('Weather property').run()
    assert not app.exception
    assert app.session_state['weather_property']=='temperature_2m_mean'


def test_map_region_mapping_covers_all_areas():
    from src.maps import REGION_TO_AREA,AREA_TO_REGION,load_geometries
    geometries=load_geometries()
    assert set(REGION_TO_AREA)==set(geometries)
    assert AREA_TO_REGION[('VASS',3)]=='VASS3' and AREA_TO_REGION[('NO',0)]=='NATIONAL'


def test_correlation_page():
    app=run_page('8_Correlation.py')
    assert len(app.metric)==3
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app.slider[1].set_value(4).run()
    assert not app.exception


def test_forecast_page_default_and_snarimax_with_exogenous():
    app=run_page('9_Forecast.py')
    assert len(app.metric)==4 and not app.error
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app.radio(key='forecast_model').set_value('snarimax').run()
        app.multiselect[0].set_value(['weather','currency']).run()
    assert not app.exception and not app.error


def test_forecast_follows_map_time_frame():
    with patch('nve_api.load_reservoir_data',return_value=reservoir_fixture()):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        app.session_state['time_frame']=(pd.Timestamp('2024-03-03'),pd.Timestamp('2024-08-25'))
        app.switch_page('pages/9_Forecast.py').run()
    assert not app.exception and not app.error
    assert app.toggle[0].value

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
    #the complete mean only contains temperature and precipitation, so the property list is shorter
    assert app.selectbox(key='spc_property').value=='temperature_2m'

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
