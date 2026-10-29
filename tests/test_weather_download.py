"""verify download safety, response validation and cache reuse without network."""
from unittest.mock import Mock
import json
import pandas as pd
import pytest
from src import weather

def test_rate_limit_stops_immediately():
    session=Mock();session.get.return_value.status_code=429
    with pytest.raises(weather.WeatherRateLimit):weather.download_point(63,10,'2024-01-01','2024-01-01',session)
    assert session.get.call_count==1

def test_bulk_requires_approval(tmp_path,monkeypatch):
    region_dir=tmp_path/'data/regions';region_dir.mkdir(parents=True)
    pd.DataFrame({'region':['NO3','NO3'],'point_id':[0,1],'latitude':[63,64],'longitude':[10,11]}).to_csv(region_dir/'points.csv',index=False)
    monkeypatch.setattr(weather,'ROOT',tmp_path)
    with pytest.raises(PermissionError):weather.download_region('NO3','2024-01-01','2024-01-01')

def test_resume_uses_cached_points_and_exact_spatial_mean(tmp_path,monkeypatch):
    region_dir=tmp_path/'data/regions';region_dir.mkdir(parents=True)
    pd.DataFrame({'region':['NO3','NO3'],'point_id':[0,1],'latitude':[63,64],'longitude':[10,11]}).to_csv(region_dir/'points.csv',index=False)
    monkeypatch.setattr(weather,'ROOT',tmp_path);monkeypatch.setattr(weather,'WEATHER_DIR',tmp_path/'weather')
    calls=[]
    def point(lat,lon,start,end,session,**kwargs):
        calls.append(lat)
        return pd.DataFrame({'temperature_2m':lat,'precipitation':1.},index=weather.expected_hours(start,end)),{}
    monkeypatch.setattr(weather,'download_point',point)
    core=weather.CORE_VARIABLES
    result=weather.download_region('NO3','2024-01-01','2024-01-01',approved=True,delay=0,variables=core)
    assert len(calls)==2 and (result.temperature_2m==63.5).all()
    #the second run must reuse both cached points without new requests
    result2=weather.download_region('NO3','2024-01-01','2024-01-01',approved=True,delay=0,variables=core)
    assert len(calls)==2
    pd.testing.assert_frame_equal(result,result2)
    #an incomplete sample (2 of 1000 points) is never saved as a regional mean
    assert not list((tmp_path/'weather').glob('*_mean.parquet'))


def fake_payload(latitude,temperature,start='2024-01-01'):
    #minimal open meteo response for one location and one day
    times=[t.strftime('%Y-%m-%dT%H:%M') for t in weather.expected_hours(start,start)]
    hourly={'time':times,**{v:[0.]*24 for v in weather.VARIABLES}}
    hourly['temperature_2m']=[temperature]*24
    return {'latitude':latitude,'longitude':10.,'elevation':100.,'timezone':'GMT',
            'hourly_units':dict(weather.UNITS),'hourly':hourly}


def test_several_locations_in_one_request_and_sample_mean(tmp_path,monkeypatch):
    region_dir=tmp_path/'data/regions';region_dir.mkdir(parents=True)
    pd.DataFrame({'region':['NO3']*3,'point_id':[0,1,2],'latitude':[63,64,65],'longitude':[10,11,12]}).to_csv(region_dir/'points.csv',index=False)
    monkeypatch.setattr(weather,'ROOT',tmp_path)
    session=Mock();session.get.return_value.status_code=200
    session.get.return_value.json.return_value=[fake_payload(63,1.),fake_payload(64,3.)]
    mean,meta=weather.download_sample('NO3','2024-01-01','2024-01-01',n_points=2,session=session)
    #one request with both coordinates, and the mean of the two locations
    assert session.get.call_count==1
    assert session.get.call_args.kwargs['params']['latitude']=='63.000000,64.000000'
    assert (mean.temperature_2m==2.).all() and list(mean.columns)==weather.VARIABLES
    assert meta['points']==2 and len(meta['grid_cells'])==2


def test_unexpected_units_rejected():
    payload=fake_payload(63,1.);payload['hourly_units']['temperature_2m']='°F'
    session=Mock();session.get.return_value.status_code=200;session.get.return_value.json.return_value=payload
    with pytest.raises(ValueError):weather.download_point(63,10,'2024-01-01','2024-01-01',session)
