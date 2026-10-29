# IND320: Norwegian reservoirs, electricity and weather

An interactive analysis project connecting Norwegian reservoir statistics, cross-border electricity flows and historical weather. The same Streamlit application is used throughout all project parts.

- **Application:** https://dano22222-u9jpvjhwntlcuukcush85v.streamlit.app/
- **Repository:** https://github.com/dano22222/dano22222
- **Development:** `part3-development`; merge into `main` with visible merge history before submission.

## Project parts

| Part | Scope |
|---|---|
| 1 | Explore reservoir CSV data with Pandas and Matplotlib; document the analysis in Jupyter; introduce Streamlit tables and plots. |
| 2 | Access NVE and ENTSO-E APIs; process electricity flows with Spark; store them in Cassandra and MongoDB Atlas; extend Streamlit. |
| 3 | Sample NVE regions, retrieve hourly ERA5 weather and analyse precipitation with DCT/SPC, temperature with LOF, and reservoir filling with STL and a spectrogram. |

## Structure

```text
app.py                         existing deployment entry point
nve_api.py                     existing cached NVE loader
pages/                         original and new Streamlit pages
src/                           reusable analysis, geography, weather and UI code
scripts/                       data preparation, approved download and notebook export
tests/                         scientific, downloader and Streamlit checks
notebooks/                     Part 1 and Part 2 copies; Part 3 working notebook
reports/                       log, AI documentation, figures, exports and video script
data/regions/                  official polygons, shapefiles and fixed sample points
data/reservoir.parquet         reproducible NVE snapshot
data/weather/                  completed weather means and local point cache
backups/                       preserved files from before Part 3 changes
requirements.txt               app dependencies
requirements-dev.txt           testing and notebook dependencies
```

Historical root notebooks, PDFs and videos remain where they were. Notebook copies in `notebooks/` do not replace the originals. Existing README screencast information is retained in `backups/part2_before_part3/README.MD`. Use the existing Part 2 video link in its notebook for that submission.

## Installation

Use Python 3.11 or 3.12 from the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

For the existing electricity page, provide `MONGODB_URI` in a local `.env` or Streamlit Cloud secrets. The notebook for Part 2 additionally requires its existing ENTSO-E token, Spark, Java and a running Cassandra instance. These services are not required to run the new Part 3 numerical tests. Never commit `.env`, tokens or secrets.

## Run Streamlit

```bash
python -m streamlit run app.py
```

The navigation groups reservoir data, plotting and seasonality together, followed by weather and electricity. Reservoir and weather pages share an area selection. Reservoir Data filters both its overview and detailed records by an inclusive date interval, with matching CSV export. Existing area comparison remains available on Reservoir Plots.

## Prepare Part 3 data

Official NVE geography and reservoir inputs are included. To deliberately refresh them:

```bash
python scripts/prepare_data.py
```

This exports source polygons as GeoJSON and shapefiles and samples 1000 points per region in an equal-area projection. The weather function accepts region and date interval and looks up these fixed coordinates. See `reports/ASSUMPTIONS.md` for the important distinction between administrative region proxies and true catchments, and the current VASS3/VASS4 metadata discrepancy.

Estimate before downloading:

```bash
python scripts/download_weather.py --region NO3 --estimate
python scripts/download_weather.py --region NO3 --pilot
```

The user approved the full NO3/2024 experiment after an estimate. To start or resume that approved run:

```bash
python scripts/download_weather.py --region NO3 --approved
```

The pointwise implementation requests 1000 point-years (8,784,000 point-hours). Requests are cached; HTTP 429 stops the run without discarding data. Long date intervals count as multiple API units. A completed 1000-point mean has a `_mean.parquet` suffix and provenance JSON. The `_pilot_1.parquet` file is a single point and is never silently treated as a regional average. Read the latest download log and status report before claiming completion. No paid subscription is required or enabled.

The app uses complete local means and offers an explicit single-point API request. Large downloads do not start during ordinary Streamlit page reruns. Completed small regional means should be included in Git; bulk point caches are ignored.

## Analysis and verification

```bash
python -m pytest -q
python scripts/build_notebook.py
python scripts/execute_notebook.py
```

Tests check deterministic geographic sampling and containment, leap-year coverage, downloader approval/cache/rate-limit behaviour, known seasonal signals, injected outliers, STL reconstruction, an annual spectrogram peak, invalid input and Streamlit controls. The electricity page is preserved; local fixture-based page tests do not verify deployed MongoDB credentials.

Open `notebooks/IND320_Project(P3).ipynb`. The notebook uses the complete regional mean when present, otherwise clearly labels a pilot and marks the regional analysis incomplete. Run it after the full download before exporting. `scripts/execute_notebook.py` creates an executed notebook and HTML with code, messages, tables and plots; run `python scripts/export_pdf.py` to generate the PDF, then visually inspect it. The PDF export includes every code cell and saved output.

Defaults: SPC cutoff 30 days and 3 robust sigmas; LOF 1% and 48 neighbours; STL annual period 52 weeks, seasonal smoother 13, trend smoother 105, robust fitting; spectrogram window 156 weeks and overlap 130. All parameters are explained in the notebook and app. Statistical flags describe unusual observations, not proven errors or causes.

## Feedback and submission

Part 2 feedback is incorporated through the date interval, clearer graphs, shared filtering, organised notebook/report folders and this README. AI usage and the technical log are in `reports/`. Review the log and add personal reflections. Follow `reports/DELIVERY_CHECKLIST.md` and the five minute script in `reports/SCREENCAST.md`.

Keep the existing app URL. The remote history was checked and contains the Part 2 merge commit `8dbf70b`. Part 3 must likewise have a visible merge from its development branch into main. The user subsequently authorized completion, including the necessary publication steps; delivery status records what was actually performed. Record the screencast personally and insert its accessible link into the notebook or Canvas comment.

## Data attribution

- [NVE reservoir statistics](https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/) and official NVE ArcGIS regional polygons; see recorded source URLs in `data/regions/provenance.json`.
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), ERA5 / Copernicus reanalysis; weather data CC BY 4.0. Spatial sampling, averages and analyses are transformations performed in this project.
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), Part 2 cross-border electricity data.
