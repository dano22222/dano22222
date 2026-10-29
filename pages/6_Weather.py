"""weather page: outlier/spc and anomaly/lof analyses of hourly era5 weather.

the weather data follow the global area selector in the sidebar (the same
selector used for the reservoir statistics). when the area or year changes,
a small regional sample is downloaded directly from open-meteo in the
background and cached, so no separate download page is needed.
"""
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from nve_api import load_reservoir_data
from src.ui import area_selector, analysis_summary
from src.geography import region_key
from src.weather import (VARIABLES, WEATHER_DIR, WeatherRateLimit, download_sample,
                         estimate_download, load_region)
from src.analysis import spc_analysis, lof_analysis


@st.cache_data(ttl=None, max_entries=64, show_spinner=False)
def get_weather(region, year, n_points):
    """download (once per region, year and sample size) the mean of n_points sampled locations."""
    return download_sample(region, f'{year}-01-01', f'{year}-12-31', n_points)


st.title('Weather outliers and anomalies')
st.write('Hourly ERA5 reanalysis from Open-Meteo for the area chosen in the sidebar. Times are in UTC.')

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
    n_points = st.select_slider('Locations in the regional sample', options=[1, 3, 5, 10, 20], value=5,
                                help='The first locations of the 1000 random points sampled for this region.')
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
        with st.spinner(f'Downloading ERA5 weather for {region}, {year}...'):
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
    st.dataframe(weather.describe().T, use_container_width=True)
    if 'locations' in metadata:
        st.map(pd.DataFrame(metadata['locations']).rename(columns={'latitude': 'lat', 'longitude': 'lon'}))
    st.download_button('Download weather data', weather.to_csv().encode(),
                       file_name=f'{region}_{year}_weather.csv', mime='text/csv')

outlier_tab, anomaly_tab = st.tabs(['Outlier / SPC', 'Anomaly / LOF'])

with outlier_tab:
    #dct cutoff and number of robust standard deviations, with the notebook defaults
    cutoff = st.slider('DCT cutoff period (days)', 2, 180, 30,
                       help='Variations slower than this period form the seasonal baseline.')
    sigma = st.slider('Number of robust standard deviations', 1., 8., 3., .25)
    fig, table, summary = spc_analysis(weather.precipitation, cutoff, sigma)
    st.pyplot(fig)
    plt.close(fig)
    analysis_summary(summary)
    st.caption('The limits are the seasonal baseline plus the median ± the chosen number of robust standard '
               'deviations (MAD) of the high-pass filtered precipitation, estimated over the whole year. '
               f"Robust standard deviation: {summary['robust_sigma']:.4f} mm per hour.")
    if summary['zero_scale']:
        st.warning('The robust spread is zero, so the limits collapse onto the baseline. Interpret flags cautiously.')
    #list the flagged hours with their limits
    st.dataframe(table.loc[table.outlier], use_container_width=True)
    st.download_button('Download SPC results', table.to_csv().encode(), file_name=f'{region}_{year}_spc.csv')

with anomaly_tab:
    #share of hours treated as anomalies (default 1 %) and neighbourhood size
    contamination = st.slider('Proportion of outliers (%)', .1, 10., 1., .1) / 100
    neighbors = st.slider('LOF neighbours', 5, 200, 48)
    fig, table, summary = lof_analysis(weather.temperature_2m, contamination, neighbors)
    st.pyplot(fig)
    plt.close(fig)
    analysis_summary(summary)
    st.caption('LOF uses standardized temperature and hourly temperature change. The proportion is an '
               'assumption, so flagged hours are unusual, not necessarily errors.')
    st.dataframe(table.loc[table.outlier].sort_values('lof_score', ascending=False), use_container_width=True)
    st.download_button('Download LOF results', table.to_csv().encode(), file_name=f'{region}_{year}_lof.csv')

st.caption('Sources: Open-Meteo Historical Weather API (ERA5, Copernicus), CC BY 4.0; NVE regional polygons. '
           'Spatial means are computed in this project.')
