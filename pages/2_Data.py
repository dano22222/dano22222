
import streamlit as st
import pandas as pd
from nve_api import load_reservoir_data
from src.ui import area_selector
from src.reservoir import filter_dates

#displaying the title of the data page
st.title("Reservoir Data")
st.write("Explore Norwegian reservoir statistics from the NVE API.")

#loading the reservoir data directly from nve
df = load_reservoir_data()

#shared geographical selection persists across reservoir and analysis pages.
selected_type, selected_area = area_selector(df)
type_df = df[df["area_type"] == selected_type].copy()

#apply the inclusive date interval to both the overview and underlying rows.
limits = (type_df.date.min().date(), type_df.date.max().date())
date_interval = st.date_input("Date interval", value=limits,
                              min_value=limits[0], max_value=limits[1])
if len(date_interval) != 2:
    st.info("Choose both a start and an end date.")
    st.stop()
type_df = filter_dates(type_df, *date_interval)
if type_df.empty:
    st.info("No observations in this date interval.")
    st.stop()

#then selecting the relevant numerical columns
numeric_columns = [
    "fill_level",
    "capacity_TWh",
    "stored_energy_TWh",
    "fill_level_previous_week",
    "change_in_fill_level"
]

#to create a summary table showing all areas of the selected type, each row represents an area number, with line charts over time
summary_rows = []

for area_number, area_data in type_df.groupby("area"):
    area_data = area_data.sort_values("date")

    row = {"Area": area_number}

    for column in numeric_columns:
        row[column] = area_data[column].dropna().tolist()

    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows).sort_values("Area")

#displaying line charts for every area number
st.subheader(f"{selected_type} Area Overview")
st.write(
    "Each row shows the development of reservoir variables "
    "over time for one area."
)

st.dataframe(
    summary_df,
    column_config={
        column: st.column_config.LineChartColumn(
            column.replace("_", " ").title()
        )
        for column in numeric_columns
    },
    hide_index=True,
    use_container_width=True
)

#showing data for the selected area
filtered_df = type_df[
    type_df["area"] == selected_area
].sort_values("date")

st.write(f"Showing data for {selected_type} area {selected_area}")

#displaying the underlying dataset
st.subheader("Reservoir Dataset")
st.dataframe(
    filtered_df,
    hide_index=True,
    use_container_width=True
)

#export exactly the area and interval currently visible.
st.download_button("Download selected data", filtered_df.to_csv(index=False).encode("utf-8"),
                   file_name=f"reservoir_{selected_type}_{selected_area}.csv", mime="text/csv")
