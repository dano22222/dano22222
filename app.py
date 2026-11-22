"""entry point of the streamlit app (the same url is used for all project parts).

run locally with: streamlit run app.py
st.navigation groups the pages into four sections that follow the type of
task (see the navigation sketch in the part 4 notebook):
  start      overview and the map, where the global area and time frame are chosen
  explore    exploratory views of each data source
  anomalies  outliers, anomalies and seasonal structure
  predict    relations between the sources and forecasting of reservoir filling
each page shows a coloured band in the colour of its group.
"""
import streamlit as st
#importing the theme registers the common plotly template for all pages
from src import theme

st.set_page_config(page_title='IND320 Reservoir Analysis', page_icon='💧', layout='wide')

#sidebar sections and their pages, in the order they are shown
pages = {
    'Start': [st.Page('pages/1_Home.py', title='Overview', icon=':material/home:', default=True),
              st.Page('pages/7_Map.py', title='Map and selection', icon=':material/map:')],
    'Explore': [st.Page('pages/2_Data.py', title='Data overview', icon=':material/table_chart:'),
                st.Page('pages/3_Plot.py', title='Reservoir plots', icon=':material/show_chart:'),
                st.Page('pages/4_Electricity.py', title='Electricity flows', icon=':material/bolt:')],
    'Anomalies': [st.Page('pages/6_Weather.py', title='Weather SATV and LOF', icon=':material/thunderstorm:'),
                  st.Page('pages/5_Seasonality.py', title='STL and spectrogram', icon=':material/waves:')],
    'Predict': [st.Page('pages/8_Correlation.py', title='Weather correlation', icon=':material/compare_arrows:'),
                st.Page('pages/9_Forecast.py', title='Forecast filling', icon=':material/trending_up:')],
}
st.navigation(pages).run()
