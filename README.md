# IND320: Norwegian reservoirs, electricity and weather

An interactive analysis project connecting Norwegian reservoir statistics (NVE), cross-border electricity flows (ENTSO-E) and historical weather (Open-Meteo ERA5). The same Streamlit application is used throughout all project parts.

- **Application:** https://dano22222-u9jpvjhwntlcuukcush85v.streamlit.app/
- **Repository:** https://github.com/dano22222/dano22222
- **Branches:** each part is developed in its own branch (`part2-development`, `part3-development`) and merged into `main` after the previous peer review and feedback.

## Project parts

| Part | Scope |
|---|---|
| 1 | Explore reservoir data with Pandas and Matplotlib; first Streamlit tables and plots. |
| 2 | NVE and ENTSO-E APIs; Spark, Cassandra and MongoDB Atlas; electricity page in Streamlit. |
| 3 | NVE regions and 1000 random locations per region; hourly ERA5 weather; precipitation outliers (DCT/SPC), temperature anomalies (LOF), STL and spectrogram of reservoir filling. |

## Structure

```text
app.py              streamlit entry point and page navigation
nve_api.py          cached download of nve reservoir data for the app
pages/              streamlit pages
src/                shared code: analysis, geography, weather download, reservoir helpers, ui
scripts/            prepare_data.py (polygons, points, reservoir snapshot), download_weather.py (full download)
tests/              pytest tests for analyses, downloads, geography and streamlit pages
notebooks/          jupyter notebooks for parts 1, 2 and 3
reports/            pdf exports of the hand-ins
data/regions/       nve polygons (geojson and shapefiles) and the sampled locations
data/reservoir.parquet          nve snapshot used by the notebook
data/weather/                   1000 point regional mean for NO3 2024 (the point cache is not in git)
requirements.txt    app dependencies (pinned); requirements-dev.txt adds testing and notebook tools
```

## Installation and running

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
python -m pytest -q
```

The electricity page needs `MONGODB_URI` in a local `.env` file or in the Streamlit Cloud secrets. Never commit `.env`, tokens or secrets.

## Part 3 data

- `python scripts/prepare_data.py` downloads the NVE electricity areas and NVE regions, builds the reservoir areas (NO1–NO5, VASS1 = RS+RØ, VASS2 = RV, VASS3 = RM+RN, Norway) and samples 1000 locations per region with a fixed seed. `--saved` rebuilds from the saved polygons.
- `python scripts/download_weather.py --estimate` prints the size and API quota estimate; `--region NO3 --approved` runs (or resumes) the full 1000 point download. A full year costs about 26 Open-Meteo call units per location (free limit 10 000 per day), so the download stops at the quota and continues from the cache the next time.
- The Streamlit weather page downloads a small sample (default 5 locations) for the selected area directly from Open-Meteo and caches it.

Default parameters: SPC cutoff 30 days and 3 robust standard deviations; LOF 1% and 48 neighbours; STL period 52 weeks, seasonal smoother 13, trend smoother 105, robust; spectrogram window 156 weeks and overlap 130.

## Data attribution

- [NVE reservoir statistics](https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/) and NVE map layers (see `data/regions/provenance.json`).
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), ERA5 / Copernicus, CC BY 4.0.
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), cross-border electricity data (Part 2).
