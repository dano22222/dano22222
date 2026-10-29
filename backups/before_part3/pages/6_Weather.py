"""Part 3 weather control and SPC/LOF tabs; never launch bulk download on rerun."""
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from nve_api import load_reservoir_data
from src.ui import area_selector
from src.geography import ROOT,region_key
from src.weather import load_region,download_region,estimate_download,WeatherRateLimit
from src.analysis import spc_analysis,lof_analysis
st.title('Weather outliers and anomalies')
st.write('Hourly ERA5 reanalysis: temperature and precipitation. Dates use UTC.')
try:
    kind,area=area_selector(load_reservoir_data());region=region_key(kind,area)
except Exception as e:st.error(f'Unable to load area selection: {e}');st.stop()
year=int(st.number_input('Weather year',min_value=1940,max_value=2025,value=2024,step=1))
start,end=f'{year}-01-01',f'{year}-12-31'
if kind=='VASS':st.warning('VASS geography follows the assignment’s RS+RØ / RV / RM+RN grouping of NVE administrative regions; this is a spatial proxy, not an exact hydrological catchment.')
with st.expander('Weather data and download control'):
    st.write(estimate_download(start,end))
    points=pd.read_csv(ROOT/'data/regions/points.csv');points=points.loc[points.region==region]
    st.map(points.rename(columns={'latitude':'lat','longitude':'lon'}))
    st.info('The full 1000-point download runs locally using scripts/download_weather.py --approved. The app only starts a small single-point request after an explicit click.')
    if st.button('Retrieve one-point pilot from Open-Meteo'):
        try:
            with st.spinner('Retrieving one point…'):download_region(region,start,end,max_points=1)
            st.success('Pilot downloaded. Select pilot mode below to inspect it.')
        except Exception as e:st.error(str(e))
mode=st.radio('Dataset',['1000-point regional mean','Single-point pilot (not regional mean)'], key='weather_mode')
try:
    weather,metadata=load_region(region,start,end,pilot=mode.startswith('Single'))
except FileNotFoundError:
    st.info(f'No completed dataset for {region}/{year} in this mode. Use download control for a pilot or complete the local regional download.');st.stop()
except ValueError as e:st.error(str(e));st.stop()
st.caption(f'{region} | {metadata["points"]} sampled point(s) | {len(weather)} hours | ERA5 / Open-Meteo')
if metadata['points']<1000:st.warning('Pilot only: these results do not fulfil the 1000-point regional analysis.')
a,b=st.tabs(['Outlier / SPC','Anomaly / LOF'])
with a:
    cutoff=st.slider('DCT cutoff period (days)',2,180,30)
    sigma=st.slider('Robust sigma multiplier',1.,8.,3.,.25)
    fig,table,summary=spc_analysis(weather.precipitation,cutoff,sigma)
    st.pyplot(fig);plt.close(fig);st.write(summary)
    st.caption('Limits use the full-year median and Gaussian-consistent MAD of high-pass residuals. Rainfall is skewed: flags are descriptive, not a calibrated probability of rare weather.')
    if summary['zero_scale']:st.warning('Residual MAD is zero; limits collapse to the robust baseline. Interpret flags cautiously.')
    st.dataframe(table.loc[table.outlier],hide_index=False)
    st.download_button('Download SPC results',table.to_csv().encode(),file_name=f'{region}_{year}_spc.csv')
with b:
    contamination=st.slider('Assumed anomaly proportion (%)',.1,10.,1.,.1)/100
    neighbors=st.slider('LOF neighbors',5,200,48)
    fig,table,summary=lof_analysis(weather.temperature_2m,contamination,neighbors)
    st.pyplot(fig);plt.close(fig);st.write(summary)
    st.caption('LOF uses standardized temperature and hourly temperature change. The fraction is an assumption, not evidence that all flags are errors. Repeated points/grid cells are spatially dependent.')
    st.dataframe(table.loc[table.outlier],hide_index=False)
    st.download_button('Download LOF results',table.to_csv().encode(),file_name=f'{region}_{year}_lof.csv')
st.caption('Sources: Open-Meteo Historical Weather API (ERA5 / Copernicus), CC BY 4.0; NVE regional polygons. Spatial means computed by this project.')
