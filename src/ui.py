"""streamlit helpers shared by several pages.

global selections live in st.session_state under normal keys (not widget
keys), because streamlit removes widget keys when a page without that widget
is shown. the global selections are:
  reservoir_selection  (area type, area number), set in the sidebar or by a click on the map
  weather_property     the daily weather variable used by the map, the weather and correlation pages
  time_frame           (start, end) weeks chosen on the map; the forecast page can follow it
"""
import pandas as pd
import streamlit as st
from src import theme
from src.weather import DAILY_VARIABLES, WEATHER_LABELS

AREA_TYPES = ['EL', 'VASS', 'NO']
AREA_NAMES = {'EL': 'Price areas (EL)', 'VASS': 'Water areas (VASS)', 'NO': 'Whole country (NO)'}


def page_header(group, title, intro=None):
    """coloured band with the active sidebar group, followed by the page title."""
    color = theme.GROUPS[group]['color']
    st.markdown(f"<div style='border-left:6px solid {color};background:{color}14;padding:.35rem .8rem;"
                f"border-radius:4px;margin-bottom:.4rem;color:{color};font-weight:600;letter-spacing:.04em'>"
                f"{group.upper()} · <span style='font-weight:400'>{theme.GROUPS[group]['text']}</span></div>",
                unsafe_allow_html=True)
    st.title(title)
    if intro:
        st.write(intro)


def show(fig, key=None):
    """show a plotly figure with the app template (theme=None keeps our own colours)."""
    st.plotly_chart(fig, width='stretch', theme=None, key=key)


def area_label(kind, area):
    """readable name of a magasinstatistikk area, for example 'EL 3 (NO3)'."""
    if kind == 'EL':
        return f'EL {area} (NO{area})'
    if kind == 'VASS':
        return f'VASS {area}'
    return 'NO 0 (Norway)'


def set_area(kind, area):
    """store a new global area and forget the old widget values so the sidebar shows it."""
    st.session_state['reservoir_selection'] = (kind, int(area))
    for key in ['shared_type', 'shared_area']:
        st.session_state.pop(key, None)


def area_selector(df):
    """sidebar radio (area type) and selectbox (area number) shared by all reservoir and weather pages.

    this is a global setting: the choice is stored in st.session_state under
    a normal key, which survives page switches. a click on the map changes
    the same setting. returns (area_type, area).
    """
    #start from the last choice, or el 3 (no3) the first time
    previous = st.session_state.get('reservoir_selection', ('EL', 3))
    types = [t for t in AREA_TYPES if t in set(df.area_type)]
    kind = st.sidebar.radio('Choose area type', types, index=types.index(previous[0]) if previous[0] in types else 0,
                            key='shared_type', format_func=lambda t: AREA_NAMES.get(t, t))
    #only offer area numbers that exist in the nve data for this type
    areas = sorted(df.loc[df.area_type == kind, 'area'].unique().tolist())
    preferred = previous[1] if previous[0] == kind and previous[1] in areas else areas[0]
    area = st.sidebar.selectbox('Choose area', areas, index=areas.index(preferred), key='shared_area')
    st.session_state['reservoir_selection'] = (kind, int(area))
    st.sidebar.caption('Shared by all pages (also set by clicking the map).')
    return kind, area


def weather_property_selector(container=None, label='Weather property'):
    """global weather property (temperature is the default), shared by the map, weather and correlation pages."""
    container = container or st.sidebar
    current = st.session_state.get('weather_property', 'temperature_2m_mean')
    choice = container.selectbox(label, DAILY_VARIABLES, index=DAILY_VARIABLES.index(current),
                                 format_func=WEATHER_LABELS.get, key='weather_property_widget')
    st.session_state['weather_property'] = choice
    return choice


def time_frame(last_date, weeks=4):
    """the global time frame (start, end); the default is the last `weeks` weeks of reservoir data."""
    last_date = pd.Timestamp(last_date)
    default = (last_date - pd.Timedelta(weeks=weeks - 1), last_date)
    return st.session_state.get('time_frame', default)


def analysis_summary(summary):
    """three metrics: number of hours, flagged hours and flagged share."""
    observations, flagged, share = st.columns(3)
    observations.metric('Hourly observations', f"{summary['observations']:,}")
    flagged.metric('Flagged hours', f"{summary['outliers']:,}")
    share.metric('Flagged share', f"{summary['fraction']:.1%}")
