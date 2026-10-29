"""Shared persistent area selection for the reservoir and Part 3 pages."""
import streamlit as st

def area_selector(df):
    #non widget state survives streamlit's cleanup when navigating pages.
    previous=st.session_state.get('reservoir_selection',('EL',3))
    types=['EL','NO','VASS']
    kind=st.sidebar.radio('Choose area type',types,index=types.index(previous[0]),key='shared_type')
    areas=sorted(df.loc[df.area_type==kind,'area'].unique().tolist())
    preferred=previous[1] if previous[0]==kind and previous[1] in areas else areas[0]
    area=st.sidebar.selectbox('Choose area',areas,index=areas.index(preferred),key='shared_area')
    st.session_state['reservoir_selection']=(kind,int(area))
    st.sidebar.caption('This area is shared by reservoir and weather analyses.')
    return kind,area
