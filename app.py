"""entry point of the streamlit app (the same url is used for all project parts).

run locally with: streamlit run app.py
st.navigation groups the pages in the sidebar; reservoir pages come first,
then the weather analyses that depend on the same area selection, and
finally the separate electricity (mongodb) page from part 2.
"""
import streamlit as st

st.set_page_config(page_title='IND320 Reservoir Analysis', layout='wide')

#sidebar sections and their pages, in the order they are shown
pages = {
    'Project': [st.Page('pages/1_Home.py', title='Overview', default=True)],
    'Reservoirs': [st.Page('pages/2_Data.py', title='Reservoir Data'),
                   st.Page('pages/3_Plot.py', title='Reservoir Plots'),
                   st.Page('pages/5_Seasonality.py', title='STL and Spectrogram')],
    'Weather': [st.Page('pages/6_Weather.py', title='SPC and LOF')],
    'Electricity': [st.Page('pages/4_Electricity.py', title='Cross-border Flows')],
}
st.navigation(pages).run()
