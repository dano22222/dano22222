"""folium map of the magasinstatistikk areas with transparent colouring and a highlighted selection.

the polygons are the geojson files made in part 3 (data/regions/regions.geojson,
converted from the nve shapefiles). they are simplified for fast drawing in
the browser; about one kilometre of detail is enough at country scale.
"""
import json
import branca.colormap as cm
import folium
import geopandas as gpd
import numpy as np
from src.geography import REGION_DIR

#map region names in the geojson to (area type, area number) in the reservoir statistics
REGION_TO_AREA = {**{f'NO{i}': ('EL', i) for i in range(1, 6)},
                  **{f'VASS{i}': ('VASS', i) for i in range(1, 4)}, 'NATIONAL': ('NO', 0)}
AREA_TO_REGION = {value: key for key, value in REGION_TO_AREA.items()}


def layer_regions(area_type):
    """region names that belong to one area type (EL, VASS or NO)."""
    return [region for region, (kind, _) in REGION_TO_AREA.items() if kind == area_type]


def load_geometries(tolerance=.01):
    """simplified region polygons as a geojson dict keyed by region name."""
    regions = gpd.read_file(REGION_DIR / 'regions.geojson')
    regions['geometry'] = regions.geometry.simplify(tolerance, preserve_topology=True)
    features = json.loads(regions.to_json())['features']
    return {feature['properties']['region']: feature for feature in features}


def area_map(geometries, area_type, values, selected_region, colors, caption, fmt='{:.1f}'):
    """folium map with one transparent coloured polygon per area and a thick outline on the selection.

    values is a dict {region: number}; regions without a value are grey.
    """
    fmap = folium.Map(location=[65, 15], zoom_start=4, tiles='OpenStreetMap', control_scale=True)
    finite = [v for v in values.values() if v is not None and np.isfinite(v)]
    low, high = (min(finite), max(finite)) if finite else (0, 1)
    if high - low < 1e-9:
        low, high = low - .5, high + .5
    colormap = cm.LinearColormap(colors, vmin=low, vmax=high, caption=caption)
    features = []
    for region in layer_regions(area_type):
        feature = json.loads(json.dumps(geometries[region]))
        value = values.get(region)
        feature['properties'].update({'value': None if value is None or not np.isfinite(value) else float(value),
                                      'label': f"{region}: {fmt.format(value) if value is not None and np.isfinite(value) else 'no data'}",
                                      'selected': region == selected_region})
        features.append(feature)

    def style(feature):
        properties = feature['properties']
        selected = properties['selected']
        fill = colormap(properties['value']) if properties['value'] is not None else '#BBBBBB'
        #the selected area gets a thick outline in the contrast colour
        return {'fillColor': fill, 'fillOpacity': .55, 'color': '#E07A5F' if selected else '#1B2A34',
                'weight': 4.5 if selected else 1}

    folium.GeoJson({'type': 'FeatureCollection', 'features': features}, name='areas', style_function=style,
                   highlight_function=lambda f: {'weight': 3, 'fillOpacity': .7},
                   tooltip=folium.GeoJsonTooltip(fields=['label'], labels=False)).add_to(fmap)
    colormap.add_to(fmap)
    return fmap
