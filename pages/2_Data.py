
import streamlit as st
import pandas as pd
from nve_api import load_reservoir_data

# Display the title of the data page
st.title("Reservoir Data")
st.write("Explore Norwegian reservoir statistics from the NVE API.")

# Load the reservoir data directly from NVE
df = load_reservoir_data()

# Select the type of geographical area
selected_type = st.radio(
    "Choose area type",
    ["EL", "NO", "VASS"],
    horizontal=True
)

# Filter the data by the selected area type
type_df = df[df["area_type"] == selected_type].copy()

# Select the relevant numerical columns
numeric_columns = [
    "fill_level",
    "capacity_TWh",
    "stored_energy_TWh",
    "fill_level_previous_week",
    "change_in_fill_level"
]

# Create a summary table showing all areas of the selected type
# Each row represents an area number, with line charts over time
summary_rows = []

for area_number, area_data in type_df.groupby("area"):
    area_data = area_data.sort_values("date")

    row = {"Area": area_number}

    for column in numeric_columns:
        row[column] = area_data[column].dropna().tolist()

    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows).sort_values("Area")

# Display line charts for every area number
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

# Select an individual area number
selected_area = st.selectbox(
    "Choose area",
    sorted(type_df["area"].unique())
)

# Show data for the selected area
filtered_df = type_df[
    type_df["area"] == selected_area
].sort_values("date")

st.write(f"Showing data for {selected_type} area {selected_area}")

# Display the underlying dataset
st.subheader("Reservoir Dataset")
st.dataframe(
    filtered_df,
    hide_index=True,
    use_container_width=True
)
