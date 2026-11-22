"""map and selection: magasinstatistikk areas coloured by reservoir filling or a weather property.

the area type in the sidebar decides which polygons are shown (price areas,
water areas or the whole country). a click on an area selects it for every
page (the global area selection), and the selected area gets a thick
contrast outline. the time frame chosen here is global as well: the forecast
page can forecast exactly this period.
"""
import datetime as dt
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium
from nve_api import load_reservoir_data
from src import data, theme
from src.maps import AREA_TO_REGION, REGION_TO_AREA, area_map, layer_regions, load_geometries
from src.ui import page_header, area_selector, area_label, set_area, weather_property_selector, time_frame
from src.weather import WEATHER_LABELS, WEEKLY_AGGREGATION, WeatherRateLimit, latest_era5_date, elevation

page_header('Start', 'Map and selection', 'Click an area to select it for all pages. The colours show the chosen '
            'variable averaged (or summed) over the chosen time frame.')


@st.cache_data(show_spinner=False)
def geometries():
    """simplified polygons, read once per server process."""
    return load_geometries()


@st.cache_data(ttl=None, show_spinner=False)
def point_elevation(latitude, longitude):
    return elevation(latitude, longitude)


try:
    df = load_reservoir_data()
except Exception as error:
    st.error(f'Could not load reservoir data from NVE: {error}')
    st.stop()
kind, area = area_selector(df)
selected_region = AREA_TO_REGION[(kind, int(area))]

#local choice of colouring, global weather property and global time frame
left, right = st.columns([1, 1])
colour_by = left.radio('Colour areas by', ['Reservoir filling', 'Weather property'], horizontal=True, key='map_colour')
if colour_by == 'Weather property':
    weather_property = weather_property_selector(right)
last_week = df.date.max()
first_week = last_week - pd.Timedelta(weeks=52 * 10)
start, end = time_frame(last_week)
start, end = max(pd.Timestamp(start), first_week), min(pd.Timestamp(end), last_week)
frame = st.slider('Time frame (weeks ending on Sunday)', min_value=first_week.date(), max_value=last_week.date(),
                  value=(start.date(), end.date()), step=dt.timedelta(weeks=1), format='DD.MM.YYYY')
st.session_state['time_frame'] = (pd.Timestamp(frame[0]), pd.Timestamp(frame[1]))
frame_start, frame_end = st.session_state['time_frame']

#one value per area for the chosen variable and time frame
regions = layer_regions(kind)
values, caption, colors, fmt = {}, '', theme.FILL_SCALE, '{:.1f} %'
if colour_by == 'Reservoir filling':
    in_frame = df[(df.area_type == kind) & (df.date >= frame_start) & (df.date <= frame_end)]
    for region in regions:
        selected = in_frame[in_frame.area == REGION_TO_AREA[region][1]].fill_level
        values[region] = float(selected.mean() * 100) if len(selected) else None
    caption = f'Mean reservoir filling (%), {frame_start:%d.%m.%Y}–{frame_end:%d.%m.%Y}'
else:
    #the week ending on frame_start starts six days earlier; era5 has about five days delay
    first_day = frame_start - pd.Timedelta(days=6)
    last_day = min(frame_end, latest_era5_date())
    how = WEEKLY_AGGREGATION[weather_property]
    colors = theme.WEATHER_SCALES[weather_property]
    fmt = '{:.1f}'
    caption = f"{WEATHER_LABELS[weather_property]}, {'mean' if how == 'mean' else 'total'} " \
              f"{first_day:%d.%m.%Y}–{last_day:%d.%m.%Y}"
    if last_day < first_day:
        st.warning('ERA5 weather is not yet available for this time frame (about five days delay).')
    else:
        try:
            with st.spinner('Downloading ERA5 weather for the areas...'):
                daily = data.daily_weather_regions(tuple(regions), str(first_day.date()), str(last_day.date()), 3)
            for region in regions:
                column = daily[region][weather_property].dropna()
                values[region] = (column.mean() if how == 'mean' else column.sum()) if len(column) else None
        except WeatherRateLimit as error:
            st.warning(str(error))
        except (requests.RequestException, ValueError) as error:
            st.error(f'Could not download weather data from Open-Meteo: {error}')

fmap = area_map(geometries(), kind, values, selected_region, colors, caption, fmt)
output = st_folium(fmap, key=f'map_{kind}', height=560, use_container_width=True,
                   returned_objects=['last_active_drawing', 'last_clicked'])

#a new click on an area changes the global selection (old clicks are ignored)
clicked = (output or {}).get('last_active_drawing')
point = (output or {}).get('last_clicked')
if clicked and point:
    signature = (clicked['properties'].get('region'), point.get('lat'), point.get('lng'))
    if signature != st.session_state.get('map_last_click'):
        st.session_state['map_last_click'] = signature
        new_area = REGION_TO_AREA.get(signature[0])
        if new_area and new_area != (kind, int(area)):
            set_area(*new_area)
            st.rerun()

left, right = st.columns([1.3, 1])
with left:
    st.markdown(f'**Selected area:** {area_label(kind, area)} (thick orange outline). '
                'The choice is used by all reservoir, weather, correlation and forecast pages.')
    table = pd.DataFrame({'Area': list(values), caption.split(',')[0]: list(values.values())})
    st.dataframe(table, hide_index=True, width='stretch')
with right:
    #bonus: terrain height of the clicked point from the open meteo elevation api
    if point:
        try:
            height = point_elevation(round(point['lat'], 4), round(point['lng'], 4))
            st.metric('Elevation at clicked point', f'{height:,.0f} m', help=f"{point['lat']:.3f}° N, {point['lng']:.3f}° E")
        except (requests.RequestException, ValueError) as error:
            st.caption(f'Elevation not available: {error}')
    else:
        st.caption('Click the map to see the terrain height of a point (Open-Meteo elevation API).')
st.caption('Polygons: NVE price areas and NVE regions (VASS areas built from regions, see Part 3), GeoJSON. '
           'Weather: mean of three of the 1000 sampled ERA5 locations per area.')
