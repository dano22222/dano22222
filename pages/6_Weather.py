"""weather page: outlier/spc and anomaly/lof analyses of hourly era5 weather.

the weather data follow the global area selector in the sidebar (the same
selector used for the reservoir statistics). when the area or year changes,
a small regional sample is downloaded directly from open-meteo in the
background and cached, so no separate download page is needed.
"""
import pandas as pd
import requests
import streamlit as st
from nve_api import load_reservoir_data
from src.ui import area_selector, analysis_summary, page_header, show
from src.geography import region_key
from src.weather import (VARIABLES, WEATHER_DIR, WeatherRateLimit, download_sample,
                         estimate_download, load_region, HOURLY_EQUIVALENT, HOURLY_LABELS)
from src.analysis import spc_analysis, lof_analysis
from src.plots import spc_figure, satv_figure, lof_figure


@st.cache_data(ttl=None, max_entries=64, show_spinner=False)
def get_weather(region, year, n_points):
    """download (once per region, year and sample size) the mean of n_points sampled locations.

    the result is cached without expiry, so the slow first download of 100 locations is
    only made once per region and year on the server.
    """
    return download_sample(region, f'{year}-01-01', f'{year}-12-31', n_points)


page_header('Anomalies', 'Weather SATV and LOF',
            'Hourly ERA5 reanalysis from Open-Meteo for the area chosen in the sidebar. Times are in UTC.')

#global setting: the shared area selector decides which region is downloaded
try:
    kind, area = area_selector(load_reservoir_data())
    region = region_key(kind, area)
except Exception as error:
    st.error(f'Unable to load the area selection: {error}')
    st.stop()

#local setting: the weather year only applies to this page
last_year = pd.Timestamp.now(tz='UTC').year - 1
year = int(st.number_input('Weather year', min_value=1940, max_value=last_year, value=2024, step=1))
start, end = f'{year}-01-01', f'{year}-12-31'
full_available = (WEATHER_DIR / f'{region}_{start}_{end}_mean.parquet').exists()

#download settings are tucked away; the defaults work without opening this
with st.expander('Weather download settings'):
    #100 of the 1000 sampled locations by default (part 3 feedback); fewer are faster to download
    n_points = st.select_slider('Locations in the regional sample', options=[5, 10, 20, 50, 100], value=100,
                                help='The first locations of the 1000 random points sampled for this region. '
                                     '100 locations take a few minutes the first time (Open-Meteo limit per '
                                     'minute) and are cached afterwards.')
    estimate = estimate_download(start, end, n_points, VARIABLES)
    st.caption(f"{n_points} location(s) × {estimate['hours_per_point']:,} hours × {len(VARIABLES)} variables "
               f"≈ {estimate['estimated_api_call_units']:.0f} Open-Meteo call units (free limit: 10 000 per day).")
    use_full = st.checkbox('Use the complete 1000-point mean from the notebook', value=False,
                           disabled=not full_available,
                           help='Only available where the full experiment was run (NO3, 2024).')

#get the data: either the stored 1000 point mean or a live, cached download
if use_full:
    weather, metadata = load_region(region, start, end)
    source = f'{region} | complete mean of 1000 sampled locations (downloaded in the notebook)'
else:
    try:
        with st.spinner(f'Downloading ERA5 weather for {n_points} locations in {region}, {year}. '
                        'The first download of 100 locations takes a few minutes; later visits use the cache.'):
            weather, metadata = get_weather(region, year, n_points)
    except WeatherRateLimit as error:
        st.warning(f'{error} Try again later, or choose fewer locations.')
        st.stop()
    except (requests.RequestException, ValueError) as error:
        st.error(f'Could not download weather data from Open-Meteo: {error}')
        st.stop()
    source = f'{region} | mean of {metadata["points"]} randomly sampled location(s) downloaded from Open-Meteo'
st.caption(f'{source} | {len(weather):,} hours | ERA5')

#show what was downloaded: all variables, the sample locations and a csv export
with st.expander('Downloaded data'):
    st.dataframe(weather.describe().T, width='stretch')
    if 'locations' in metadata:
        st.map(pd.DataFrame(metadata['locations']).rename(columns={'latitude': 'lat', 'longitude': 'lon'}))
    st.download_button('Download weather data', weather.to_csv().encode(),
                       file_name=f'{region}_{year}_weather.csv', mime='text/csv')

outlier_tab, anomaly_tab = st.tabs(['Outlier / SPC (SATV)', 'Anomaly / LOF'])

#the default property follows the global weather property (temperature the first time)
default_property = HOURLY_EQUIVALENT.get(st.session_state.get('weather_property', 'temperature_2m_mean'), 'temperature_2m')
properties = [v for v in VARIABLES if v in weather.columns]
default_index = properties.index(default_property) if default_property in properties else 0


def check_values(series):
    """stop with a clear message if the downloaded series has missing values."""
    if series.isna().any():
        st.warning(f'{series.isna().sum()} hours are missing for this property, so the analysis is not run.')
        return False
    return True


with outlier_tab:
    #local settings: property, dct cutoff and number of robust standard deviations
    left, middle, right = st.columns(3)
    spc_property = left.selectbox('Weather property', properties, index=default_index,
                                  format_func=HOURLY_LABELS.get, key='spc_property')
    cutoff = middle.slider('DCT cutoff period (days)', 2, 180, 30,
                           help='Variations slower than this period form the seasonal baseline.')
    sigma = right.slider('Number of robust standard deviations', 1., 8., 3., .25)
    label = HOURLY_LABELS[spc_property]
    if check_values(weather[spc_property]):
        try:
            _, table, summary = spc_analysis(weather[spc_property], cutoff, sigma, label=label, plot=False)
            show(spc_figure(table, label))
            show(satv_figure(table, label))
            analysis_summary(summary)
            st.caption('The SATV are the high-pass filtered values (original minus the DCT baseline). The limits are '
                       'the baseline plus the median ± the chosen number of robust standard deviations (MAD) of the '
                       f"SATV over the whole year. Robust standard deviation: {summary['robust_sigma']:.4f}.")
            if summary['zero_scale']:
                st.warning('The robust spread is zero, so the limits collapse onto the baseline. Interpret flags cautiously.')
            with st.expander(f"Flagged hours ({summary['outliers']})"):
                st.dataframe(table.loc[table.outlier], width='stretch')
            st.download_button('Download SPC results', table.to_csv().encode(), file_name=f'{region}_{year}_{spc_property}_spc.csv')
        except ValueError as error:
            st.warning(f'SPC could not be computed: {error}')

with anomaly_tab:
    #local settings: property, share of hours treated as anomalies (default 1 %) and neighbourhood size
    left, middle, right = st.columns(3)
    lof_property = left.selectbox('Weather property', properties, index=default_index,
                                  format_func=HOURLY_LABELS.get, key='lof_property')
    contamination = middle.slider('Proportion of outliers (%)', .1, 10., 1., .1) / 100
    neighbors = right.slider('LOF neighbours', 5, 200, 48)
    label = HOURLY_LABELS[lof_property]
    if check_values(weather[lof_property]):
        try:
            _, table, summary = lof_analysis(weather[lof_property], contamination, neighbors, label=label, plot=False)
            show(lof_figure(table, label))
            analysis_summary(summary)
            st.caption('LOF uses the standardized value and its hourly change. The proportion is an '
                       'assumption, so flagged hours are unusual, not necessarily errors.')
            with st.expander(f"Flagged hours ({summary['outliers']})"):
                st.dataframe(table.loc[table.outlier].sort_values('lof_score', ascending=False), width='stretch')
            st.download_button('Download LOF results', table.to_csv().encode(), file_name=f'{region}_{year}_{lof_property}_lof.csv')
        except ValueError as error:
            st.warning(f'LOF could not be computed: {error}')

st.caption('Sources: Open-Meteo Historical Weather API (ERA5, Copernicus), CC BY 4.0; NVE regional polygons. '
           'Spatial means are computed in this project.')
