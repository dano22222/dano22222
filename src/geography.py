"""official nve polygons and reproducible random sampling of locations.

the reservoir statistics (magasinstatistikk) use three area types:
  EL    electricity price areas NO1 to NO5
  VASS  watercourse (precipitation) areas 1 to 3
  NO    the whole country (area 0)

the polygons come from the same nve map services that atlas.nve.no displays:
  electricity areas: layer "Elspotområder" (Omradekonsesjoner/MapServer/8)
  nve regions:       layer "NVE regioner"   (Administrasjon/MapServer/0)

the VASS areas have no polygon layer of their own, so they are built from the
five nve regions, following the assignment text:
  VASS1 (east)  = RS + RØ
  VASS2 (west)  = RV
  VASS3 (north) = RM + RN
the reservoir data only contains VASS1, VASS2 and VASS3, and their capacities
add up to the national capacity, which confirms that VASS3 covers both RM and RN.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely import contains_xy

#project root, so paths work from the notebook, the scripts and streamlit
ROOT = Path(__file__).resolve().parents[1]
REGION_DIR = ROOT / 'data/regions'

#arcgis rest layers behind the electricity area and nve region maps
SOURCES = {
    'electricity': 'https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/8',
    'administrative': 'https://gis3.nve.no/map/rest/services/Mapservices/Administrasjon/MapServer/0',
}

#which nve regions are merged into each watercourse area
VASS_REGIONS = {
    'VASS1': ['RS', 'RØ'],
    'VASS2': ['RV'],
    'VASS3': ['RM', 'RN'],
}


def query_polygons(url):
    """download every feature of one nve map layer as a geodataframe in wgs84."""
    response = requests.get(url + '/query',
                            params={'where': '1=1', 'outFields': '*', 'outSR': 4326, 'f': 'geojson'},
                            timeout=120)
    response.raise_for_status()
    payload = response.json()
    #stop if the service reports an error or truncates the result
    if 'error' in payload or payload.get('exceededTransferLimit'):
        raise ValueError(f'Incomplete NVE response: {payload.get("error")}')
    return gpd.GeoDataFrame.from_features(payload['features'], crs=4326)


def sample_polygon(geometry, count=1000, seed=320, original_wgs84=None):
    """draw count uniformly distributed random points inside a polygon.

    geometry must be in the equal area projection epsg:3035, so that every
    square kilometre has the same chance of being chosen. rejection sampling is
    used: random points are drawn in the bounding box and only points inside
    the polygon are kept. the result is returned as longitude/latitude.
    """
    if count < 1 or geometry.is_empty:
        raise ValueError('Nonempty polygon and positive count required.')
    #a fixed seed makes the sample identical every time it is regenerated
    rng = np.random.default_rng(seed)
    xmin, ymin, xmax, ymax = geometry.bounds
    points = []
    for _ in range(10000):
        #draw a batch of candidates in the bounding box
        x = rng.uniform(xmin, xmax, max(1000, count * 2))
        y = rng.uniform(ymin, ymax, len(x))
        inside = contains_xy(geometry, x, y)
        accepted_x, accepted_y = x[inside], y[inside]
        if original_wgs84 is not None:
            #check again after reprojection, because polygon edges bend slightly between projections
            candidate = gpd.GeoSeries(gpd.points_from_xy(accepted_x, accepted_y), crs=3035).to_crs(4326)
            valid = contains_xy(original_wgs84, candidate.x.to_numpy(), candidate.y.to_numpy())
            accepted_x, accepted_y = accepted_x[valid], accepted_y[valid]
        points.extend(zip(accepted_x, accepted_y))
        if len(points) >= count:
            break
    if len(points) < count:
        raise ValueError('Sampling failed: extremely sparse polygon.')
    xy = np.asarray(points[:count])
    return gpd.GeoSeries(gpd.points_from_xy(xy[:, 0], xy[:, 1]), crs=3035).to_crs(4326)


def build_regions(electricity, administrative):
    """combine the two nve layers into one polygon per reservoir statistics area."""
    rows = []
    #electricity areas: merge all parts with the same code (for example islands)
    for name, group in electricity.groupby('ElSpotOmr'):
        key = str(name).strip().upper().replace(' ', '')
        if not key.startswith('NO'):
            key = 'NO' + key
        rows.append({'region': key, 'geometry': group.geometry.union_all()})
    #watercourse areas: merge the nve regions listed in the vass mapping above
    for key, codes in VASS_REGIONS.items():
        selected = administrative.loc[administrative.REGION.isin(codes)]
        if selected.REGION.nunique() != len(codes):
            raise ValueError(f'Missing NVE regions for {key}: {codes}')
        rows.append({'region': key, 'geometry': selected.geometry.union_all()})
    #the whole country is the union of all nve regions
    rows.append({'region': 'NATIONAL', 'geometry': administrative.geometry.union_all()})
    regions = gpd.GeoDataFrame(rows, crs=4326).sort_values('region').reset_index(drop=True)
    if not {'NO1', 'NO2', 'NO3', 'NO4', 'NO5'}.issubset(regions.region):
        raise ValueError('Unexpected electricity codes.')
    return regions


def prepare_regions(count=1000, seed=320, from_saved=False):
    """download (or reload) the polygons, save them and sample count points per region.

    from_saved=True rebuilds everything from the geojson files already in
    data/regions, so no network access is needed.
    """
    REGION_DIR.mkdir(parents=True, exist_ok=True)
    if from_saved:
        electricity = gpd.read_file(REGION_DIR / 'electricity.geojson')
        administrative = gpd.read_file(REGION_DIR / 'administrative.geojson')
    else:
        electricity = query_polygons(SOURCES['electricity'])
        administrative = query_polygons(SOURCES['administrative'])
        #keep the original layers both as geojson and as shapefiles
        for name, gdf in [('electricity', electricity), ('administrative', administrative)]:
            gdf.to_file(REGION_DIR / f'{name}.geojson', driver='GeoJSON')
            folder = REGION_DIR / name
            folder.mkdir(exist_ok=True)
            gdf.to_file(folder / f'{name}.shp', driver='ESRI Shapefile', encoding='UTF-8')
    regions = build_regions(electricity, administrative)
    regions.to_file(REGION_DIR / 'regions.geojson', driver='GeoJSON')
    #sample in the equal area projection, with a different but fixed seed per region
    projected = regions.to_crs(3035)
    samples = []
    for i, row in projected.iterrows():
        points = sample_polygon(row.geometry, count, seed + i, regions.loc[i].geometry)
        samples.append(pd.DataFrame({'region': row.region, 'point_id': range(count),
                                     'longitude': points.x, 'latitude': points.y}))
    pd.concat(samples, ignore_index=True).to_csv(REGION_DIR / 'points.csv', index=False)
    #record where the data came from and how the sample was made
    (REGION_DIR / 'provenance.json').write_text(json.dumps({
        'sources': SOURCES, 'seed': seed, 'points_per_region': count, 'sampling_crs': 'EPSG:3035',
        'vass_regions': VASS_REGIONS,
        'note': 'VASS areas are built from NVE regions (an administrative approximation, not exact catchments).'},
        indent=2, ensure_ascii=False))
    return regions


def region_key(area_type, area):
    """translate a reservoir area selection (for example EL 3) into a region name (NO3)."""
    if area_type == 'EL':
        return f'NO{int(area)}'
    if area_type == 'VASS' and f'VASS{int(area)}' in VASS_REGIONS:
        return f'VASS{int(area)}'
    if area_type == 'NO' and int(area) == 0:
        return 'NATIONAL'
    raise ValueError('Unsupported reservoir area.')
