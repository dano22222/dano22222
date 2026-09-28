import streamlit as st
import pandas as pd

#display the title of the data page
st.title("Reservoir Data")


#load and cache the reservoir data to avoid unnecessary reloading
@st.cache_data
def load_data():
    df = pd.read_csv("reservoirs.csv")

    #rename the original norwegian columns to clear english names
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

    return df


#load the prepared reservoir data
df = load_data()

#select the numerical columns from the dataset
numeric_columns = df.select_dtypes(include="number").columns

#create one row for each numerical column using the first observations
table_data = pd.DataFrame({
    "Column": numeric_columns,
    "First month": [
        df[column].head(4).tolist()
        for column in numeric_columns
    ]
})

#display the first observations as small line charts inside the table
st.dataframe(
    table_data,
    column_config={
        "First month": st.column_config.LineChartColumn(
            "First month"
        )
    },
    hide_index=True
)