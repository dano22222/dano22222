"""Single existing deployment entry point; keep the original Streamlit URL."""
import streamlit as st
st.set_page_config(page_title='IND320 Reservoir Analysis',layout='wide')
pages={
 'Project':[st.Page('pages/1_Home.py',title='Overview',default=True)],
 'Reservoirs':[st.Page('pages/2_Data.py',title='Reservoir Data'),
               st.Page('pages/3_Plot.py',title='Reservoir Plots'),
               st.Page('pages/5_Seasonality.py',title='STL and Spectrogram')],
 'Weather':[st.Page('pages/6_Weather.py',title='SPC and LOF')],
 'Electricity':[st.Page('pages/4_Electricity.py',title='Cross-border Flows')]
}
st.navigation(pages).run()
