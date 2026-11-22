"""front page: what the app contains, the active global selections and links to the four groups."""
import streamlit as st
from src import theme
from src.ui import page_header, area_label

page_header('Start', 'Norwegian reservoirs, weather, electricity and currency',
            'An interactive project connecting NVE reservoir statistics (Magasinstatistikk), '
            'ERA5 weather (Open-Meteo), cross-border electricity flows (ENTSO-E via MongoDB) '
            'and exchange rates (Norges Bank).')

#current global selections, so the user knows what the other pages will show
kind, area = st.session_state.get('reservoir_selection', ('EL', 3))
frame = st.session_state.get('time_frame')
left, right = st.columns(2)
left.metric('Selected area', area_label(kind, area))
right.metric('Map time frame', f'{frame[0]:%d.%m.%Y} – {frame[1]:%d.%m.%Y}' if frame else 'Last 4 weeks (default)')

#one card per sidebar group, in the group colour, with links to its pages
groups = {
    'Start': [('pages/7_Map.py', 'Map and selection', 'Click an area to select it for all pages; choose the time frame.')],
    'Explore': [('pages/2_Data.py', 'Data overview', 'Reservoir tables, sparklines and exchange rates.'),
                ('pages/3_Plot.py', 'Reservoir plots', 'Filling and capacity per area and period.'),
                ('pages/4_Electricity.py', 'Electricity flows', 'Imports and exports NO2–DK1 from MongoDB.')],
    'Anomalies': [('pages/6_Weather.py', 'Weather SATV and LOF', 'Outliers and anomalies in hourly weather.'),
                  ('pages/5_Seasonality.py', 'STL and spectrogram', 'Seasonal structure of reservoir filling.')],
    'Predict': [('pages/8_Correlation.py', 'Weather correlation', 'Sliding window correlation with lag.'),
                ('pages/9_Forecast.py', 'Forecast filling', 'SARIMAX or lag based ML with River.')],
}
for column, (group, links) in zip(st.columns(4), groups.items()):
    with column:
        color = theme.GROUPS[group]['color']
        st.markdown(f"<div style='border-top:5px solid {color};padding-top:.3rem'><b style='color:{color}'>"
                    f"{group}</b><br><span style='font-size:.9em'>{theme.GROUPS[group]['text']}</span></div>",
                    unsafe_allow_html=True)
        for path, title, text in links:
            st.page_link(path, label=title)
            st.caption(text)

st.divider()
st.markdown('**How selections work.** The area (sidebar or map click), the weather property and the map time frame '
            'are global and follow you between pages. Year, window lengths and model settings are local to each page.')
st.markdown('[GitHub repository](https://github.com/dano22222/dano22222)')
