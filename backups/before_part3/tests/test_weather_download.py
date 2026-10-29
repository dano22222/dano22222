"""Verify download safety, response validation and cache reuse without network."""
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
    def point(lat,lon,start,end,session):
        calls.append(lat)
        return pd.DataFrame({'temperature_2m':lat,'precipitation':1.},index=weather.expected_hours(start,end)),{}
    monkeypatch.setattr(weather,'download_point',point)
    result=weather.download_region('NO3','2024-01-01','2024-01-01',approved=True,delay=0)
    assert len(calls)==2 and (result.temperature_2m==63.5).all()
    result2=weather.download_region('NO3','2024-01-01','2024-01-01',approved=True,delay=0)
    assert len(calls)==2
    pd.testing.assert_frame_equal(result,result2)
    meta=json.loads(next((tmp_path/'weather').glob('*pilot_2.json')).read_text())
    assert not meta['complete_1000']
