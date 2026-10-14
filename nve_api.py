
import pandas as pd
import requests
import streamlit as st

# Official NVE reservoir statistics API
NVE_URL = (
    "https://biapi.nve.no/magasinstatistikk/"
    "api/Magasinstatistikk/HentOffentligData"
)


@st.cache_data(ttl=3600)
def load_reservoir_data():
    """Download and prepare Norwegian reservoir data from NVE."""

    # Retrieve the dataset directly from the API
    response = requests.get(NVE_URL, timeout=60)
    response.raise_for_status()

    df = pd.DataFrame(response.json())

    # Rename Norwegian columns to descriptive English names
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

    # Convert and sort dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["date"])
    df = df.sort_values(
        ["area_type", "area", "date"]
    ).reset_index(drop=True)

    return df

