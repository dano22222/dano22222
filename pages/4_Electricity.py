
import os
import calendar
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


# Page title
st.title("Cross-Border Electricity Flows")
st.write(
    "Explore electricity imports and exports between "
    "Norway and neighbouring countries."
)


# Connect to MongoDB Atlas
@st.cache_resource
def get_collection():
    load_dotenv()

    # Local development uses .env
    mongo_uri = os.getenv("MONGODB_URI")

    # Streamlit Cloud uses secrets
    if not mongo_uri:
        try:
            mongo_uri = st.secrets["MONGODB_URI"]
        except (KeyError, FileNotFoundError):
            raise RuntimeError("MongoDB credentials are missing.")

    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=10000
    )

    client.admin.command("ping")

    return client["ind320"]["cross_border_flows"]


# Cache database queries to avoid repeated downloads
@st.cache_data(ttl=3600)
def load_electricity_data(connection, year):
    collection = get_collection()

    cursor = collection.find(
        {
            "connection": connection,
            "year": int(year)
        },
        {
            "_id": 0,
            "connection": 1,
            "direction": 1,
            "timestamp": 1,
            "year": 1,
            "month": 1,
            "power_mw": 1,
            "energy_mwh": 1
        }
    )

    df = pd.DataFrame(list(cursor))

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

    return df


# Establish connection and identify available connections
try:
    collection = get_collection()
    connections = sorted(collection.distinct("connection"))
except (PyMongoError, RuntimeError):
    st.error(
        "Could not connect to MongoDB Atlas. "
        "Check your credentials and network access."
    )
    st.stop()

if not connections:
    st.warning("No electricity flow data found in MongoDB.")
    st.stop()


# Split the page into two columns
left_col, right_col = st.columns(2, gap="large")


# LEFT COLUMN: connection, year and pie chart
with left_col:
    st.subheader("Annual Electricity Exchange")

    selected_connection = st.radio(
        "Choose connection",
        connections
    )

    available_years = sorted(
        collection.distinct(
            "year",
            {"connection": selected_connection}
        ),
        reverse=True
    )

    default_year = (
        2025 if 2025 in available_years
        else available_years[0]
    )

    selected_year = st.selectbox(
        "Choose year",
        available_years,
        index=available_years.index(default_year)
    )


# Retrieve the selected year's data
try:
    df = load_electricity_data(
        selected_connection,
        selected_year
    )
except PyMongoError:
    st.error("Could not retrieve electricity data from MongoDB.")
    st.stop()

if df.empty:
    st.warning("No data available for this selection.")
    st.stop()


with left_col:
    # Aggregate energy by import and export direction
    energy_totals = (
        df.groupby("direction")["energy_mwh"]
        .sum()
    )

    if energy_totals.sum() > 0:
        fig, ax = plt.subplots(figsize=(5, 4))

        ax.pie(
            energy_totals.values,
            labels=energy_totals.index,
            autopct="%1.1f%%",
            startangle=90
        )

        ax.set_title(
            f"{selected_connection} ({selected_year})"
        )
        ax.axis("equal")

        st.pyplot(fig)
        plt.close(fig)

        st.caption("Total recorded energy exchange in MWh.")
    else:
        st.info("No energy exchange recorded for this year.")


# RIGHT COLUMN: month selection and line chart
with right_col:
    st.subheader("Electricity Flow Over Time")

    available_months = sorted(
        df["month"].dropna().astype(int).unique()
    )

    month_options = [
        calendar.month_name[month]
        for month in available_months
    ]

    selected_months = st.pills(
        "Choose months",
        options=month_options,
        selection_mode="multi",
        default=month_options[:1]
    )

    if selected_months:
        selected_month_numbers = [
            list(calendar.month_name).index(month)
            for month in selected_months
        ]

        monthly_df = df[
            df["month"].isin(selected_month_numbers)
        ].copy()

        # Create separate lines for import and export
        plot_df = monthly_df.pivot_table(
            index="timestamp",
            columns="direction",
            values="power_mw",
            aggfunc="mean"
        ).sort_index()

        if not plot_df.empty:
            st.line_chart(plot_df)

            st.caption(
                f"Power in MW. Showing "
                f"{len(monthly_df):,} observations."
            )
        else:
            st.info("No data for the selected months.")
    else:
        st.info("Select at least one month.")


# Document the data source
st.divider()

with st.expander("About the data source"):
    st.write(
        "Electricity flow data are retrieved from the "
        "ENTSO-E Transparency Platform API."
    )

    st.write(
        "The data were processed using Apache Spark "
        "and stored in a local Cassandra database. "
        "Selected observations were then transferred "
        "to MongoDB Atlas."
    )

    st.write(
        "This Streamlit page reads the data directly "
        "from MongoDB Atlas."
    )

    st.write(
        "The pie chart shows the share of recorded "
        "imported and exported energy during the "
        "available period of the selected year. "
        "The line chart shows power in MW for "
        "the selected months."
    )
