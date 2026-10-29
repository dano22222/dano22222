"""Part 3 reservoir analyses reuse one selected area and the same weekly series."""
import streamlit as st
import matplotlib.pyplot as plt
from nve_api import load_reservoir_data
from src.ui import area_selector
from src.reservoir import weekly_series
from src.analysis import stl_analysis,spectrogram_analysis
st.title('Reservoir seasonality')
st.write('Explore long-term filling patterns for one area. Weekly observations; annual period ≈52 weeks.')
try:
    df=load_reservoir_data();kind,area=area_selector(df);series=weekly_series(df,kind,area)
except Exception as e:
    st.error(f'Unable to prepare reservoir data: {e}');st.stop()
st.caption(f'{kind} {area} | {series.index.min():%Y-%m-%d} – {series.index.max():%Y-%m-%d} | {len(series)} weeks')
a,b=st.tabs(['STL decomposition','Spectrogram'])
with a:
    seasonal=st.slider('Seasonal smoother (odd)',3,53,13,2)
    trend=st.slider('Trend smoother (odd, >52)',53,209,105,2)
    robust=st.checkbox('Robust STL',value=True)
    try:
        fig,result=stl_analysis(series,seasonal,trend,robust);st.pyplot(fig);plt.close(fig)
        st.caption('Observed filling fraction = trend + seasonal component + residual. Robust fitting reduces the influence of unusual weeks.')
    except ValueError as e:st.warning(str(e))
with b:
    window=st.slider('Window length (weeks)',52,260,156,26)
    overlap=st.slider('Overlap (weeks)',0,window-1,min(130,window-1))
    try:
        fig,result=spectrogram_analysis(series,window,overlap);st.pyplot(fig);plt.close(fig)
        st.caption(f'Frequency resolution: {52/window:.3f} cycles/year. A frequency of 1 corresponds to an annual pattern. Longer windows improve frequency resolution but blur changes over time.')
    except ValueError as e:st.warning(str(e))
