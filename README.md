# IND320: Norwegian reservoirs, electricity and weather

An interactive analysis project connecting Norwegian reservoir statistics (NVE), cross-border electricity flows (ENTSO-E) and historical weather (Open-Meteo ERA5). The same Streamlit application is used throughout all project parts.

- **Application:** https://dano22222-u9jpvjhwntlcuukcush85v.streamlit.app/
- **Repository:** https://github.com/dano22222/dano22222
- **Branches:** each part is developed in its own branch (`part2-development`, `part3-development`, `part4-development`) and merged into `main` after the previous peer review and feedback.

## Project parts

| Part | Scope |
|---|---|
| 1 | Explore reservoir data with Pandas and Matplotlib; first Streamlit tables and plots. |
| 2 | NVE and ENTSO-E APIs; Spark, Cassandra and MongoDB Atlas; electricity page in Streamlit. |
| 3 | NVE regions and 1000 random locations per region; hourly ERA5 weather; precipitation outliers (DCT/SPC), temperature anomalies (LOF), STL and spectrogram of reservoir filling. |
| 4 | Norges Bank exchange rates; timezone investigation; River forecasting (SNARIMAX and lag based ML) with quantile intervals; sliding window correlation; app refactoring (theme, Plotly, grouped navigation) with an interactive map, correlation and forecast pages. |

## Structure

```text
app.py              streamlit entry point and grouped page navigation (start, explore, anomalies, predict)
.streamlit/         app theme (config.toml)
nve_api.py          cached download of nve reservoir data for the app
pages/              streamlit pages
src/                shared code: analysis, geography, weather (hourly and daily), reservoir helpers, currency (norges bank),
                    forecast (river), correlation, plots and theme (plotly), maps (folium), data (cached loaders), ui
scripts/            prepare_data.py (polygons, points, reservoir snapshot), download_weather.py (full download),
                    make_navigation_sketch.py (figure in the part 4 notebook)
tests/              pytest tests for analyses, downloads, geography and streamlit pages
notebooks/          jupyter notebooks for parts 1 to 4 (figures/ holds the navigation sketch)
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

## Part 4 app

- **Start:** overview and *Map and selection* (Folium map of the price areas, water areas or the whole country, coloured by reservoir filling or a weather property over a chosen time frame; a click selects the area for all pages and shows the terrain elevation).
- **Explore:** data overview (NVE sparklines and table, Norges Bank exchange rates), reservoir plots, electricity flows.
- **Anomalies:** weather SATV/SPC and LOF with a weather property selector (temperature by default), STL and spectrogram.
- **Predict:** sliding window correlation between weather and the weekly change in filling, and River forecasts of the filling with selectable model, parameters, exogenous sources, training period and horizon (can follow the map time frame), animated in Plotly with quantile intervals.

The area, weather property and map time frame are global selections in `st.session_state`. Forecast defaults (`src/forecast.DEFAULTS`) come from the backtests in the Part 4 notebook.

Default parameters (Part 3): SPC cutoff 30 days and 3 robust standard deviations; LOF 1% and 48 neighbours; STL period 52 weeks, seasonal smoother 13, trend smoother 105, robust; spectrogram window 156 weeks and overlap 130.

## Data attribution

- [NVE reservoir statistics](https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/) and NVE map layers (see `data/regions/provenance.json`).
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), ERA5 / Copernicus, CC BY 4.0.
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), cross-border electricity data (Part 2).
- [Norges Bank open data](https://www.norges-bank.no/en/topics/Statistics/open-data/), EUR and USD exchange rates (Part 4).
- [Open-Meteo Elevation API](https://open-meteo.com/en/docs/elevation-api) (Part 4 map).
