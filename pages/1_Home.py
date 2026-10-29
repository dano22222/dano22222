"""overview page with a short guide to the other pages."""
import streamlit as st

st.title('IND320: reservoirs, electricity and weather')
st.write('Explore Norwegian reservoir statistics, cross-border electricity flows and historical ERA5 weather.')
#short description of each sidebar section
st.markdown(
    '- **Reservoirs:** NVE reservoir statistics as tables and plots, plus STL decomposition and spectrogram.\n'
    '- **Weather:** precipitation outliers (DCT/SPC) and temperature anomalies (LOF) from Open-Meteo ERA5 data.\n'
    '- **Electricity:** cross-border flows from ENTSO-E, stored in MongoDB (Part 2).\n\n'
    'The area chosen in the sidebar is shared by the reservoir and weather pages.')
st.markdown('[GitHub repository](https://github.com/dano22222/dano22222)')
