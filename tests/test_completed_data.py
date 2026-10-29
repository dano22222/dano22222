"""check the delivered regional dataset once the approved download is complete"""
import json
import numpy as np
import pandas as pd
import pytest
from src.weather import WEATHER_DIR,load_region,VARIABLES

@pytest.mark.skipif(not (WEATHER_DIR/'NO3_2024-01-01_2024-12-31_mean.parquet').exists(),reason='regional download still running')
def test_completed_mean_matches_all_1000_points():
    mean,meta=load_region('NO3')
    folder=WEATHER_DIR/meta['point_cache']
    if not folder.exists():
        pytest.skip('raw point cache is local and not distributed with git')
    files=sorted(folder.glob('point_*.parquet'))
    assert len(files)==1000 and len(mean)==8784 and meta['model']=='era5'
    total=np.zeros((8784,2),dtype='float64')
    for path in files:
        point=pd.read_parquet(path)
        assert point.index.equals(mean.index)
        assert np.isfinite(point[VARIABLES].to_numpy()).all()
        total+=point[VARIABLES].to_numpy()
    np.testing.assert_allclose(mean[VARIABLES].to_numpy(),total/1000,rtol=0,atol=1e-10)


@pytest.mark.skipif(not (WEATHER_DIR/'NO3_2024-01-01_2024-12-31_mean.parquet').exists(),reason='regional download still running')
def test_distributed_regional_mean_and_provenance():
    mean,meta=load_region('NO3')
    assert meta['complete_1000'] and meta['points']==1000
    assert meta['model']=='era5' and meta['timezone']=='UTC'
    assert list(mean.columns)==VARIABLES
    assert len(mean)==8784 and np.isfinite(mean.to_numpy()).all()
    assert mean.index.min()==pd.Timestamp('2024-01-01T00:00:00Z')
    assert mean.index.max()==pd.Timestamp('2024-12-31T23:00:00Z')
