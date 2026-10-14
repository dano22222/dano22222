
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
type_df = df[df["area_type"] == selected_type]

# Select an area number
selected_area = st.selectbox(
    "Choose area",
    sorted(type_df["area"].unique())
)

# Show data for the selected area
filtered_df = type_df[
    type_df["area"] == selected_area
].sort_values("date")

st.write(f"Showing data for {selected_type} area {selected_area}")

# Select the relevant numerical columns
numeric_columns = [
    "fill_level",
    "capacity_TWh",
    "stored_energy_TWh",
    "fill_level_previous_week",
    "change_in_fill_level"
]

# Create a summary table with small line charts
table_data = pd.DataFrame({
    "Column": numeric_columns,
    "First observations": [
        filtered_df[column].head(4).tolist()
        for column in numeric_columns
    ]
})

st.dataframe(
    table_data,
    column_config={
        "First observations": st.column_config.LineChartColumn(
            "First observations"
        )
    },
    hide_index=True
)

# Display the underlying dataset
st.subheader("Reservoir Dataset")
st.dataframe(filtered_df, hide_index=True)
