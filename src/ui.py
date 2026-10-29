"""streamlit helpers shared by several pages."""
import streamlit as st


def area_selector(df):
    """sidebar radio (area type) and selectbox (area number) shared by all reservoir and weather pages.

    this is a global setting: the choice is stored in st.session_state under
    a normal key, which survives page switches (widget keys are cleared by
    streamlit when a page without the widget is shown). returns (area_type, area).
    """
    #start from the last choice, or el 3 (no3) the first time
    previous = st.session_state.get('reservoir_selection', ('EL', 3))
    types = ['EL', 'NO', 'VASS']
    kind = st.sidebar.radio('Choose area type', types, index=types.index(previous[0]), key='shared_type')
    #only offer area numbers that exist in the nve data for this type
    areas = sorted(df.loc[df.area_type == kind, 'area'].unique().tolist())
    preferred = previous[1] if previous[0] == kind and previous[1] in areas else areas[0]
    area = st.sidebar.selectbox('Choose area', areas, index=areas.index(preferred), key='shared_area')
    st.session_state['reservoir_selection'] = (kind, int(area))
    st.sidebar.caption('This area is shared by the reservoir and weather pages, '
                       'and decides which weather data are downloaded.')
    return kind, area


def analysis_summary(summary):
    """three metrics: number of hours, flagged hours and flagged share."""
    observations, flagged, share = st.columns(3)
    observations.metric('Hourly observations', f"{summary['observations']:,}")
    flagged.metric('Flagged hours', f"{summary['outliers']:,}")
    share.metric('Flagged share', f"{summary['fraction']:.1%}")
