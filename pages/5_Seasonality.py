"""reservoir seasonality page: stl decomposition and spectrogram in two tabs.

both tabs use the weekly filling fraction of the area chosen in the shared
sidebar selector (the same global selector as the other reservoir pages).
"""
import streamlit as st
from nve_api import load_reservoir_data
from src.ui import area_selector, area_label, page_header, show
from src.reservoir import weekly_series
from src.analysis import stl_analysis, spectrogram_analysis
from src.plots import stl_figure, spectrogram_figure

page_header('Anomalies', 'STL and spectrogram',
            'Long-term filling patterns for one area. Weekly observations; annual period ≈52 weeks.')

#reservoir data come directly from the nve api (cached in nve_api.py)
try:
    df = load_reservoir_data()
    kind, area = area_selector(df)
    series = weekly_series(df, kind, area)
except Exception as error:
    st.error(f'Unable to prepare reservoir data: {error}')
    st.stop()
st.caption(f'{area_label(kind, area)} | {series.index.min():%Y-%m-%d} – {series.index.max():%Y-%m-%d} | {len(series)} weeks')

stl_tab, spectrogram_tab = st.tabs(['STL decomposition', 'Spectrogram'])

with stl_tab:
    #loess window lengths must be odd; the trend window must be longer than one year
    seasonal = st.slider('Seasonal smoother (odd, weeks)', 3, 53, 13, 2)
    trend = st.slider('Trend smoother (odd, weeks, >52)', 53, 209, 105, 2)
    robust = st.checkbox('Robust STL', value=True)
    try:
        _, result = stl_analysis(series, seasonal, trend, robust, plot=False)
        show(stl_figure(result))
        st.caption('Observed filling fraction = trend + seasonal component + residual. '
                   'Robust fitting reduces the influence of unusual weeks.')
    except ValueError as error:
        st.warning(str(error))

with spectrogram_tab:
    #window length and overlap in weeks; the overlap must be shorter than the window
    window = st.slider('Window length (weeks)', 52, 260, 156, 26)
    overlap = st.slider('Window overlap (weeks)', 0, window - 1, min(130, window - 1))
    try:
        _, result = spectrogram_analysis(series, window, overlap, plot=False)
        show(spectrogram_figure(result))
        st.caption(f'Frequency resolution: {52 / window:.3f} cycles/year. A frequency of 1 corresponds to an '
                   'annual pattern. Longer windows improve frequency resolution but blur changes over time. '
                   'The plot focuses on 0–6 cycles/year; the full spectrum extends to 26. '
                   'Only complete windows are shown.')
    except ValueError as error:
        st.warning(str(error))
