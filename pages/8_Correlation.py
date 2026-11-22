"""sliding window correlation between a weekly weather property and the reservoir statistics.

the weather is the weekly regional mean (sum for amounts) for the area in
the sidebar, on the same sunday based weeks as magasinstatistikk. the
representative reservoir variable is the weekly change in filling, which
reacts directly to inflow (rain, snow melt), while the filling level itself is
dominated by the seasonal cycle.
"""
import pandas as pd
import requests
import streamlit as st
from nve_api import load_reservoir_data
from src import data
from src.correlation import sliding_correlation, lag_scan
from src.geography import region_key
from src.plots import correlation_figure, lag_scan_figure
from src.ui import page_header, area_selector, area_label, weather_property_selector, show
from src.weather import WEATHER_LABELS, WeatherRateLimit, latest_era5_date

page_header('Predict', 'Weather correlation',
            'Sliding window correlation with selectable lag and window length between weather and reservoir filling.')

try:
    df = load_reservoir_data()
except Exception as error:
    st.error(f'Could not load reservoir data from NVE: {error}')
    st.stop()
kind, area = area_selector(df)
region = region_key(kind, area)

#global weather property, local reservoir variable and period
left, right = st.columns(2)
weather_property = weather_property_selector(left, 'Meteorological property')
reservoir_names = {'change': 'Weekly change in filling (percentage points)', 'level': 'Filling (%)'}
reservoir_variable = right.selectbox('Reservoir variable', list(reservoir_names), format_func=reservoir_names.get)
last_year = min(df.date.max().year, latest_era5_date().year)
years = st.slider('Years', 1996, last_year, (max(1996, last_year - 9), last_year),
                  help='Ten years of daily weather for three locations is about 800 Open-Meteo call units, cached afterwards.')
lag_col, window_col = st.columns(2)
lag = lag_col.slider('Lag (weeks, positive = weather leads)', -26, 26, 0)
window = window_col.slider('Window length (weeks)', 4, 104, 26, 2)

#weekly reservoir series of the selected area (percent)
level = (df[(df.area_type == kind) & (df.area == area)].set_index('date').fill_level.sort_index() * 100)
level = level.reindex(pd.date_range(level.index.min(), level.index.max(), freq='W-SUN'))
reservoir = level.diff() if reservoir_variable == 'change' else level
start = f'{years[0]}-01-01'
end = str(min(pd.Timestamp(f'{years[1]}-12-31'), latest_era5_date()).date())
try:
    with st.spinner(f'Downloading daily ERA5 weather for {region}, {years[0]}–{years[1]}...'):
        weather = data.weekly_weather(region, start, end, 3)[weather_property]
    frame = sliding_correlation(weather, reservoir.loc[start:end], lag, window)
    scan = lag_scan(weather, reservoir.loc[start:end])
except WeatherRateLimit as error:
    st.warning(str(error))
    st.stop()
except (requests.RequestException, ValueError) as error:
    st.error(f'Could not compute the correlation: {error}')
    st.stop()

overall = scan.get(lag)
best = scan.abs().idxmax()
columns = st.columns(3)
columns[0].metric(f'Correlation at lag {lag}', f'{overall:.2f}' if pd.notna(overall) else 'n/a')
columns[1].metric('Strongest lag', f'{best} weeks', f'r = {scan[best]:.2f}', delta_color='off')
columns[2].metric('Windows with |r| > 0.5', f'{(frame.correlation.abs() > .5).mean():.0%}')
show(correlation_figure(frame, WEATHER_LABELS[weather_property], reservoir_names[reservoir_variable], lag, window))
show(lag_scan_figure(scan, lag))
st.caption(f'{area_label(kind, area)} | weather: mean of three sampled ERA5 locations in {region}, aggregated to '
           'weeks ending on Sunday (Europe/Oslo days). Windows with fewer than 80% valid weeks are left empty.')
