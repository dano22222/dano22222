"""cross-border electricity flows (part 2 data in mongodb atlas) with interactive plotly charts.

timestamps are stored in utc; they are shown in europe/oslo time here, and
the month filter uses oslo months (see the timezone section in the part 4 notebook).
"""
import calendar
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo.errors import PyMongoError
from src import theme
from src.data import mongo_collection
from src.ui import page_header, show

page_header('Explore', 'Electricity flows', 'Electricity imports and exports between Norway (NO2) and Denmark (DK1), '
            'from ENTSO-E via Cassandra to MongoDB Atlas.')


@st.cache_data(ttl=3600, show_spinner=False)
def load_electricity_data(connection, year):
    """all observations of one connection and year, with local (oslo) time added."""
    cursor = mongo_collection().find({"connection": connection, "year": int(year)},
                                     {"_id": 0, "connection": 1, "direction": 1, "timestamp": 1,
                                      "power_mw": 1, "energy_mwh": 1})
    df = pd.DataFrame(list(cursor))
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["local_time"] = df["timestamp"].dt.tz_convert("Europe/Oslo")
        df["month"] = df["local_time"].dt.month
        df = df.sort_values("timestamp")
    return df


#establishing the connection and identifying available connections
try:
    with st.spinner('Connecting to MongoDB Atlas...'):
        collection = mongo_collection()
        connections = sorted(collection.distinct("connection"))
except (PyMongoError, RuntimeError) as error:
    st.error(f"Could not connect to MongoDB Atlas ({error}). Check the credentials and network access.")
    st.stop()
if not connections:
    st.warning("No electricity flow data found in MongoDB.")
    st.stop()

left_col, right_col = st.columns([1, 1.6], gap="large")

with left_col:
    st.subheader("Annual exchange")
    selected_connection = st.radio("Choose connection", connections, horizontal=True)
    available_years = sorted(collection.distinct("year", {"connection": selected_connection}), reverse=True)
    default_year = 2025 if 2025 in available_years else available_years[0]
    selected_year = st.selectbox("Choose year", available_years, index=available_years.index(default_year))

#retrieve the selected year's data
try:
    with st.spinner('Loading electricity data...'):
        df = load_electricity_data(selected_connection, selected_year)
except PyMongoError as error:
    st.error(f"Could not retrieve electricity data from MongoDB: {error}")
    st.stop()
if df.empty or df["energy_mwh"].isna().all():
    st.warning("No data available for this selection.")
    st.stop()

with left_col:
    #share of exported and imported energy in the year (missing values are ignored)
    energy_totals = df.groupby("direction")["energy_mwh"].sum(min_count=1).dropna()
    if energy_totals.sum() > 0:
        fig = go.Figure(go.Pie(labels=energy_totals.index, values=energy_totals.values, hole=.45,
                               marker=dict(colors=[theme.PRIMARY, theme.ACCENT]),
                               hovertemplate='%{label}<br>%{value:,.0f} MWh<br>%{percent}<extra></extra>'))
        fig.update_layout(title=f"{selected_connection} ({selected_year})", height=360, legend=dict(y=-.15, x=0, xanchor='left'))
        show(fig)
        st.caption("Total recorded energy exchange in MWh.")
    else:
        st.info("No energy exchange recorded for this year.")

with right_col:
    st.subheader("Flow over time")
    available_months = sorted(df["month"].dropna().astype(int).unique())
    month_options = [calendar.month_name[month] for month in available_months]
    selected_months = st.pills("Choose months", options=month_options, selection_mode="multi", default=month_options[:1])
    if selected_months:
        numbers = [list(calendar.month_name).index(month) for month in selected_months]
        monthly_df = df[df["month"].isin(numbers)]
        fig = go.Figure()
        for direction, group in monthly_df.groupby("direction"):
            fig.add_trace(go.Scatter(x=group["local_time"], y=group["power_mw"], name=direction, line=dict(width=1)))
        fig.update_layout(xaxis_title="Time (Europe/Oslo)", yaxis_title="Power (MW)", height=420, hovermode="x unified")
        show(fig)
        st.caption(f"Power in MW. Showing {len(monthly_df):,} observations.")
    else:
        st.info("Select at least one month.")

st.divider()
with st.expander("About the data source"):
    st.write("Electricity flows were retrieved from the ENTSO-E Transparency Platform API (timestamps in UTC), "
             "processed with Apache Spark, stored in Cassandra and transferred to MongoDB Atlas. This page reads "
             "MongoDB directly and converts the timestamps to Norwegian time.")
