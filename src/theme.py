"""one colour theme for the streamlit pages and every plotly figure.

the same colours are written in .streamlit/config.toml. each page group in
the sidebar has its own accent colour, shown as a coloured band at the top of
the page, so the user always sees which part of the app is active.
"""
import plotly.graph_objects as go
import plotly.io as pio

#fjord blue as the main colour, with warm and green accents
PRIMARY = '#1F6F8B'
TEXT = '#1B2A34'
BACKGROUND = '#FFFFFF'
PANEL = '#F3F7F9'
GRID = '#DCE4EA'
ACCENT = '#E07A5F'
COLORWAY = [PRIMARY, ACCENT, '#3D9970', '#C9A227', '#6C5B7B', '#8A9BA8', '#81B29A', '#B5525C']

#accent colour and short description of each sidebar group
GROUPS = {
    'Start': {'color': PRIMARY, 'text': 'Overview, map and shared selections'},
    'Explore': {'color': '#3D9970', 'text': 'Exploratory views of each data source'},
    'Anomalies': {'color': ACCENT, 'text': 'Outliers, anomalies and seasonal structure'},
    'Predict': {'color': '#6C5B7B', 'text': 'Relations between sources and forecasting'},
}

#sequential colour scales for the map and heatmaps (light to dark)
FILL_SCALE = ['#E8F1F5', '#9CC5D6', '#4F95B2', PRIMARY, '#0E3B4C']
WEATHER_SCALES = {'temperature_2m_mean': ['#2C7BB6', '#ABD9E9', '#FFFFBF', '#FDAE61', '#D7191C'],
                  'precipitation_sum': ['#F7FBFF', '#9ECAE1', '#4292C6', '#08519C', '#08306B'],
                  'rain_sum': ['#F7FBFF', '#9ECAE1', '#4292C6', '#08519C', '#08306B'],
                  'snowfall_sum': ['#FFFFFF', '#DADAEB', '#9E9AC8', '#6A51A3', '#3F007D'],
                  'wind_speed_10m_max': ['#FFF5EB', '#FDD0A2', '#FD8D3C', '#D94801', '#7F2704']}

#plotly template with the app fonts and colours
pio.templates['ind320'] = go.layout.Template(layout=go.Layout(
    colorway=COLORWAY,
    font=dict(family='Source Sans Pro, Arial, sans-serif', color=TEXT, size=13),
    paper_bgcolor=BACKGROUND, plot_bgcolor=PANEL,
    title=dict(font=dict(size=17, color=TEXT), x=0, xanchor='left'),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, bgcolor='rgba(0,0,0,0)'),
    hoverlabel=dict(bgcolor='white', font_size=12),
    margin=dict(l=60, r=20, t=60, b=50),
    colorscale=dict(sequential=FILL_SCALE)))
pio.templates.default = 'plotly_white+ind320'
