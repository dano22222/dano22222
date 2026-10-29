"""Official NVE polygons, reproducible equal-area rejection sampling."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely import contains_xy
ROOT=Path(__file__).resolve().parents[1]
REGION_DIR=ROOT/'data/regions'
SOURCES={
 'electricity':'https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/8',
 'administrative':'https://gis3.nve.no/map/rest/services/Mapservices/Administrasjon/MapServer/0'}

def query_polygons(url):
    r=requests.get(url+'/query',params={'where':'1=1','outFields':'*','outSR':4326,'f':'geojson'},timeout=120)
    r.raise_for_status();obj=r.json()
    if 'error' in obj or obj.get('exceededTransferLimit'):raise ValueError(f'Incomplete NVE response: {obj.get("error")}')
    return gpd.GeoDataFrame.from_features(obj['features'],crs=4326)

def sample_polygon(geometry, count=1000, seed=320, original_wgs84=None):
    """Uniform area in EPSG:3035 (equal-area), then convert to lon/lat."""
    if count<1 or geometry.is_empty:raise ValueError('Nonempty polygon and positive count required.')
    rng=np.random.default_rng(seed);xmin,ymin,xmax,ymax=geometry.bounds
    points=[]
    for _ in range(10000):
        x=rng.uniform(xmin,xmax,max(1000,count*2));y=rng.uniform(ymin,ymax,len(x))
        inside=contains_xy(geometry,x,y)
        accepted_x,accepted_y=x[inside],y[inside]
        if original_wgs84 is not None:
            #verify containment after transformation because polygon edges change projection
            candidate=gpd.GeoSeries(gpd.points_from_xy(accepted_x,accepted_y),crs=3035).to_crs(4326)
            valid=contains_xy(original_wgs84,candidate.x.to_numpy(),candidate.y.to_numpy())
            accepted_x,accepted_y=accepted_x[valid],accepted_y[valid]
        points.extend(zip(accepted_x,accepted_y))
        if len(points)>=count:break
    if len(points)<count:raise ValueError('Sampling failed: extremely sparse polygon.')
    xy=np.asarray(points[:count])
    return gpd.GeoSeries(gpd.points_from_xy(xy[:,0],xy[:,1]),crs=3035).to_crs(4326)

def prepare_regions(count=1000, seed=320):
    REGION_DIR.mkdir(parents=True,exist_ok=True)
    el=query_polygons(SOURCES['electricity']);admin=query_polygons(SOURCES['administrative'])
    #save original service payload geometry and requested shapefile format.
    for name,gdf in [('electricity',el),('administrative',admin)]:
        gdf.to_file(REGION_DIR/f'{name}.geojson',driver='GeoJSON')
        folder=REGION_DIR/name;folder.mkdir(exist_ok=True)
        gdf.to_file(folder/f'{name}.shp',driver='ESRI Shapefile',encoding='UTF-8')
    rows=[]
    for name,g in el.groupby('ElSpotOmr'):
        key=str(name).strip().upper().replace(' ','')
        if not key.startswith('NO'):key='NO'+key
        rows.append({'region':key,'geometry':g.geometry.union_all()})
    #assignment explicitly requests rs+rø / rv / rm+rn. administrative
    #boundaries are a stated spatial proxy, not exact hydrological catchments.
    for key,codes in {'VASS1':['RS','RØ'],'VASS2':['RV'],'VASS3':['RM'],'VASS4':['RN'],'PRECIP_NORTH':['RM','RN']}.items():
        rows.append({'region':key,'geometry':admin.loc[admin.REGION.isin(codes)].geometry.union_all()})
    rows.append({'region':'NATIONAL','geometry':admin.geometry.union_all()})
    regions=gpd.GeoDataFrame(rows,crs=4326).sort_values('region').reset_index(drop=True)
    if not set(['NO1','NO2','NO3','NO4','NO5']).issubset(regions.region):raise ValueError('Unexpected electricity codes.')
    regions.to_file(REGION_DIR/'regions.geojson',driver='GeoJSON')
    projected=regions.to_crs(3035);samples=[]
    for i,row in projected.iterrows():
        points=sample_polygon(row.geometry,count,seed+i,regions.loc[i].geometry)
        samples.append(pd.DataFrame({'region':row.region,'point_id':range(count),'longitude':points.x,'latitude':points.y}))
    pd.concat(samples,ignore_index=True).to_csv(REGION_DIR/'points.csv',index=False)
    (REGION_DIR/'provenance.json').write_text(json.dumps({'sources':SOURCES,'seed':seed,'points_per_region':count,
      'sampling_crs':'EPSG:3035','note':'VASS1=RS+RØ, VASS2=RV, VASS3=RM, VASS4=RN; PRECIP_NORTH=RM+RN is the assignment combined north. All are administrative proxies, not exact catchments. Live NVE metadata distinguishes VASS3 mid and VASS4 north.'},indent=2))
    return regions

def region_key(area_type, area):
    if area_type=='EL':return f'NO{int(area)}'
    if area_type=='VASS':return f'VASS{int(area)}'
    if area_type=='NO' and int(area)==0:return 'NATIONAL'
    raise ValueError('Unsupported reservoir area.')
