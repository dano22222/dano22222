import geopandas as gpd
import pytest
import numpy as np
import pandas as pd
from shapely.geometry import box
from src.geography import sample_polygon,ROOT,region_key

def test_area_weighted_sampling_and_reproducibility():
    polygon=box(0,0,1000,1000).union(box(2000,0,4000,1000))
    a=sample_polygon(polygon,1000,320).to_crs(3035)
    b=sample_polygon(polygon,1000,320).to_crs(3035)
    assert np.allclose(a.x,b.x) and np.allclose(a.y,b.y)
    assert a.within(polygon).all()
    assert .60<(a.x>1500).mean()<.73

def test_all_stored_points_inside_regions():
    regions=gpd.read_file(ROOT/'data/regions/regions.geojson').set_index('region')
    points=pd.read_csv(ROOT/'data/regions/points.csv')
    for key,part in points.groupby('region'):
        assert len(part)==1000 and part.point_id.nunique()==1000
        geo=gpd.GeoSeries(gpd.points_from_xy(part.longitude,part.latitude),crs=4326)
        assert geo.within(regions.loc[key].geometry).all()
    assert region_key('EL',3)=='NO3' and region_key('NO',0)=='NATIONAL'
    assert sorted(points.region.unique())==['NATIONAL','NO1','NO2','NO3','NO4','NO5','VASS1','VASS2','VASS3']


def test_vass_areas_follow_assignment_and_reservoir_data():
    #east = rs+rø, west = rv, north = rm+rn; the nve data only contain vass 1 to 3
    admin=gpd.read_file(ROOT/'data/regions/administrative.geojson').set_index('REGION')
    regions=gpd.read_file(ROOT/'data/regions/regions.geojson').set_index('region')
    north=admin.loc[['RM','RN']].geometry.union_all()
    assert abs(regions.loc['VASS3'].geometry.area-north.area)<1e-6*north.area
    reservoir=pd.read_parquet(ROOT/'data/reservoir.parquet')
    assert sorted(reservoir.loc[reservoir.area_type=='VASS','area'].unique())==[1,2,3]
    assert region_key('VASS',3)=='VASS3'
    with pytest.raises(ValueError):region_key('VASS',4)
