import streamlit as st
import pandas as pd

st.title("Reservoir Plot")


# Load and cache the reservoir data
@st.cache_data
def load_data():
    df = pd.read_csv("reservoirs.csv")

    # Rename columns to clear English names
    df = df.rename(columns={
        "dato_Id": "date",
        "omrType": "area_type",
        "omrnr": "area",
        "iso_aar": "year",
        "iso_uke": "week",
        "fyllingsgrad": "fill_level",
        "kapasitet_TWh": "capacity_TWh",
        "fylling_TWh": "stored_energy_TWh",
        "neste_Publiseringsdato": "next_publication_date",
        "fyllingsgrad_forrige_uke": "fill_level_previous_week",
        "endring_fyllingsgrad": "change_in_fill_level"
    })

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    return df


df = load_data()


# Select reservoir area
selected_area = st.selectbox(
    "Choose area",
    sorted(df["area"].unique())
)

filtered_df = df[df["area"] == selected_area].copy()


# Select one column or all columns
selected_column = st.selectbox(
    "Choose column",
    [
        "All",
        "fill_level",
        "capacity_TWh",
        "stored_energy_TWh",
        "fill_level_previous_week",
        "change_in_fill_level"
    ]
)


# Month names used by the slider
month_names = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}


# Select a range of months
selected_months = st.select_slider(
    "Choose months",
    options=list(month_names.keys()),
    value=("January", "January")
)

start_month = month_names[selected_months[0]]
end_month = month_names[selected_months[1]]


# Filter the data by selected months
filtered_df = filtered_df[
    filtered_df["date"].dt.month.between(start_month, end_month)
]


# Plot all columns or the selected column
if selected_column == "All":
    st.line_chart(
        filtered_df,
        x="date",
        y=[
            "fill_level",
            "capacity_TWh",
            "stored_energy_TWh",
            "fill_level_previous_week",
            "change_in_fill_level"
        ]
    )
else:
    st.line_chart(
        filtered_df,
        x="date",
        y=selected_column
    )