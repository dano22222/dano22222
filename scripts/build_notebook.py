"""build the part 3 notebook from reproducible code and explanatory text."""
from pathlib import Path
import nbformat as nb
ROOT=Path(__file__).resolve().parents[1]
cells=[]
def md(text):cells.append(nb.v4.new_markdown_cell(text.strip()))
def code(text):cells.append(nb.v4.new_code_cell(text.strip()))
md('''# IND320 Project Part 3
## Reservoir seasonality and weather anomalies

This notebook extends Parts 1 and 2 with official NVE geographical regions, reproducible point sampling, ERA5 weather retrieval and four analyses: DCT/SPC, Local Outlier Factor, STL and a spectrogram.

**GitHub:** https://github.com/dano22222/dano22222  
**Same Streamlit application as Parts 1 and 2:** https://dano22222-u9jpvjhwntlcuukcush85v.streamlit.app/

**Screencast:** to be recorded by the student; the prepared five minute script is in `reports/SCREENCAST.md`. Add the accessible video link here or in the Canvas submission comment before handing in.

**Completion rule:** a single-point pilot or partial cache does not fulfil the required 1000-point regional mean. The next sections report which dataset was actually analysed.''')
md('''## 1. Reproducible environment and configuration

The shared Python modules contain the production functions used by both this notebook and Streamlit. Imports do not trigger database writes or bulk downloads. The random seed is fixed during geographic preparation. Weather timestamps use UTC, avoiding daylight-saving gaps.''')
code('''#locate the project from either the root or the notebooks folder
from pathlib import Path
import sys, json, importlib.metadata
ROOT = Path.cwd()
if not (ROOT / "src").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from src.analysis import spc_analysis, lof_analysis, stl_analysis, spectrogram_analysis
from src.reservoir import weekly_series
from src.weather import load_region, estimate_download
REGION, START, END = "NO3", "2024-01-01", "2024-12-31"
print({name: importlib.metadata.version(name) for name in ["numpy", "pandas", "scipy", "scikit-learn", "statsmodels"]})''')
md('''## 2. Geographical data and 1000 reproducible locations per region

The official NVE electricity and administrative polygon layers are retrieved programmatically from the services behind the NVE maps. Their original GeoJSON, exported shapefile bundles and source provenance are retained. Uniform rejection sampling takes place in equal-area EPSG:3035, then points are transformed to longitude/latitude.

The assignment combines east as RS+RØ and north as RM+RN. Current NVE metadata separately identifies VASS3 as Midt and VASS4 as Nord, whereas the historical reservoir response currently contains VASS1–3. We therefore retain the combined northern polygon as PRECIP_NORTH and map VASS3 to RM and VASS4 to RN. These administrative polygons are explicitly spatial proxies, **not exact hydrological catchments**. NO3 uses its actual electricity-area polygon. Coastal sampling and the API's land-cell choice also limit interpretation of regional averages.''')
code('''#inspect saved official polygons and validate all sampled points
regions = gpd.read_file(ROOT / "data/regions/regions.geojson")
points = pd.read_csv(ROOT / "data/regions/points.csv")
display(points.groupby("region").size().rename("sampled locations").to_frame())
assert points.groupby("region").size().eq(1000).all()
no3 = regions.loc[regions.region == REGION]
no3_points = points.loc[points.region == REGION]
locations = gpd.GeoSeries(gpd.points_from_xy(no3_points.longitude, no3_points.latitude), crs=4326)
assert locations.within(no3.geometry.iloc[0]).all()
fig, ax = plt.subplots(figsize=(7, 7))
no3.to_crs(3035).plot(ax=ax, color="#edf3f8", edgecolor="#29485f")
locations.to_crs(3035).plot(ax=ax, markersize=3, color="#086e87", alpha=.6)
ax.set_title("NO3: 1000 uniformly sampled locations")
ax.set_xlabel("Equal area easting (m)"); ax.set_ylabel("Equal area northing (m)")
fig.tight_layout(); plt.show()
print((ROOT / "data/regions/provenance.json").read_text())''')
md('''## 3. ERA5 download, resource estimate and data quality

`download_region(region, start, end, approved=...)` looks up the saved coordinate list and retrieves at least temperature and precipitation, explicitly selecting ERA5. A full leap year has 8784 hours. Data are checked for correct units, duplicates, complete time coverage and finite values. Each successful request is cached and can be reused after an interruption. A full regional result is only published after every sampled point is represented. The user approved the full NO3 download after receiving a resource estimate. No bulk download is triggered by running this notebook.

Source: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), ERA5 / Copernicus, CC BY 4.0. This project computes spatial averages. Reanalysis and neighbouring grid cells are not independent weather-station measurements.''')
code('''#report the estimate and select only a clearly identified available dataset
print(json.dumps(estimate_download(START, END), indent=2))
try:
    weather, weather_metadata = load_region(REGION, START, END)
    regional_complete = True
except FileNotFoundError:
    weather, weather_metadata = load_region(REGION, START, END, pilot=True)
    regional_complete = False
print(json.dumps(weather_metadata, indent=2))
print("complete regional experiment:", regional_complete)
if not regional_complete:
    display(Markdown("**INCOMPLETE REGIONAL EXPERIMENT: the following weather figures use one pilot location, not the 1000-point mean. Rerun after the full download.**"))
assert len(weather) == 8784 and weather.index.is_unique
assert np.isfinite(weather.to_numpy()).all()
display(weather.describe())
display(weather.head())
if regional_complete and (ROOT / "reports/weather_audit.json").exists():
    display(pd.Series(json.loads((ROOT / "reports/weather_audit.json").read_text())).to_frame("verified result"))''')
md('''## 4. Precipitation outliers: DCT high pass and robust SPC

An orthonormal DCT-II represents the original hourly precipitation. Coefficient k has frequency k/(2 N Δt). Frequencies at or below 1/30 days form the smooth baseline; subtracting it gives the high-pass residuals. The entire year's residual median and Gaussian-consistent median absolute deviation (MAD) define robust limits at median ±3 MAD. Adding the baseline yields limits on the **original precipitation scale**. Only original precipitation, limits and contrasting outliers are plotted; residual/SATV values are not plotted.

The assignment's temperature wording in this precipitation section is interpreted as seasonally adjusted precipitation variations. Rainfall is skewed, autocorrelated and often zero, so these are descriptive control limits, not calibrated Gaussian probabilities. Zero MAD is explicitly reported. Negative lower limits are retained to show the mathematical limits and do not imply physically negative rain. Cutoff and sigma multiplier are configurable.''')
code('''#analyse precipitation and display the actual flagged observations
CUTOFF_DAYS, N_SIGMA = 30, 3
fig, spc_table, spc_summary = spc_analysis(weather.precipitation, CUTOFF_DAYS, N_SIGMA)
plt.show()
print(spc_summary)
display(spc_table.loc[spc_table.outlier].head(20))
(ROOT / "reports/figures").mkdir(parents=True, exist_ok=True)
fig.savefig(ROOT / "reports/figures/precipitation_spc.png", dpi=160, bbox_inches="tight")
spc_table.to_csv(ROOT / "reports/spc_results.csv")''')
md('''## 5. Temperature anomalies: Local Outlier Factor

LOF compares local neighbour densities using two standardized features: temperature and its hourly change. The first change is defined as zero. Defaults are 48 neighbours and 1% contamination. This can highlight unusual temperatures or rapid changes relative to the data's density. Contamination is a modelling assumption; detected anomalies are not necessarily errors. The model is descriptive and has no training/test claim or causal interpretation.''')
code('''#identify temperature anomalies using the same complete hourly time index
fig, lof_table, lof_summary = lof_analysis(weather.temperature_2m, contamination=.01, n_neighbors=48)
plt.show()
print(lof_summary)
display(lof_table.loc[lof_table.outlier].sort_values("lof_score", ascending=False).head(20))
fig.savefig(ROOT / "reports/figures/temperature_lof.png", dpi=160, bbox_inches="tight")
lof_table.to_csv(ROOT / "reports/lof_results.csv")''')
md("""### Parameter sensitivity

Outlier counts depend on modelling choices. The following checks vary the DCT cutoff and the assumed LOF contamination while holding other defaults fixed. More flags do not establish worse data quality; they show sensitivity to the definition of an unusual observation.""")
code("""#compare parameter choices without displaying additional duplicate figures
sensitivity = []
for cutoff in [7, 30, 90]:
    figure, table, summary = spc_analysis(weather.precipitation, cutoff_days=cutoff, n_sigma=3)
    plt.close(figure)
    sensitivity.append({"method": "spc", "parameter": f"cutoff {cutoff} days", "flagged": summary["outliers"]})
for fraction in [.005, .01, .02]:
    figure, table, summary = lof_analysis(weather.temperature_2m, contamination=fraction, n_neighbors=48)
    plt.close(figure)
    sensitivity.append({"method": "lof", "parameter": f"contamination {100*fraction:g}%", "flagged": summary["outliers"]})
display(pd.DataFrame(sensitivity))""")
md('''## 6. Reservoir filling: prepare a regular weekly series

Use one reservoir area's filling fraction, not an average of overlapping national and regional statistics. The included NVE snapshot makes the analysis reproducible offline; the Streamlit app continues to retrieve current data from NVE. Missing weeks and duplicate timestamps are rejected rather than silently interpolated. Several years are needed to distinguish annual seasonality from trend.''')
code('''#select the same no3 electricity area and inspect weekly coverage
reservoir = pd.read_parquet(ROOT / "data/reservoir.parquet")
filling = weekly_series(reservoir, area_type="EL", area=3)
print("weekly observations:", len(filling))
print("time interval:", filling.index.min(), filling.index.max())
print("step sizes:", filling.index.to_series().diff().dropna().value_counts().to_dict())
display(filling.describe())''')
md('''## 7. Seasonal trend decomposition using LOESS

STL separates observed filling fraction into trend, seasonal component and residual. Use annual period 52 weekly observations, seasonal smoother 13, trend smoother 105 and robust fitting by default. Smoothers must be odd; trend must exceed the seasonal period. A 52-week year approximates the true calendar year. Robust fitting reduces the influence of exceptional weeks without proving that they are erroneous.''')
code('''#decompose the entire regular weekly series and verify reconstruction
fig, stl_result = stl_analysis(filling, seasonal=13, trend=105, robust=True)
plt.show()
assert np.allclose(stl_result.trend + stl_result.seasonal + stl_result.resid, filling)
fig.savefig(ROOT / "reports/figures/reservoir_stl.png", dpi=160, bbox_inches="tight")
print("seasonal range:", float(stl_result.seasonal.max() - stl_result.seasonal.min()))
print("residual standard deviation:", float(stl_result.resid.std()))''')
md('''## 8. Spectrogram of the same filling series

A Hann-window spectrogram uses 156 weekly samples per window with 130 samples overlap. Each segment is linearly detrended. Frequencies are cycles per 52-week year; 1 cycle/year represents annual variation. The frequency resolution is 52/156 = 1/3 cycles/year. Longer windows improve frequency resolution while reducing temporal localisation. Colour represents log power density; a small floor is used only to display logarithms. The plot focuses on 0–6 cycles/year; the full computed spectrum extends to the weekly Nyquist frequency of 26 cycles/year. Only complete windows are shown, so their centres do not reach the endpoints.''')
code('''#use exactly the same weekly filling series as the stl analysis
fig, spectrum = spectrogram_analysis(filling, window=156, overlap=130)
plt.show()
fig.savefig(ROOT / "reports/figures/reservoir_spectrogram.png", dpi=160, bbox_inches="tight")
nonzero = spectrum["frequency"] > 0
frequency = spectrum["frequency"][nonzero]
mean_power = spectrum["power"][nonzero].mean(axis=1)
print("dominant nonzero frequency:", float(frequency[mean_power.argmax()]), "cycles per year")''')
md('''## 9. Function tests and scientific validation

The test suite checks known annual periodicity, STL reconstruction and seasonal recovery, injected SPC/LOF anomalies, constant signals, invalid parameters, missing timestamps, deterministic area sampling, polygon containment, download approval, cache reuse and rate-limit handling. Streamlit tests exercise date filtering, comparison controls and the new analysis pages. These tests complement scientific interpretation; they do not prove all real-weather flags are meaningful.''')
code('''#run the local test suite without making external database writes
import subprocess
check = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True)
print(check.stdout)
if check.returncode:
    print(check.stderr)
assert check.returncode == 0''')
md('''## 10. Interpretation of the actual results''')
code('''#summarize computed results while keeping completion status explicit
status = "1000 point regional mean" if regional_complete else "single point pilot only"
display(Markdown(f"""The weather results above use **{status}**. SPC flags **{spc_summary['outliers']}** of {len(weather)} hourly observations with a 30 day baseline and three robust sigmas. LOF flags **{lof_summary['outliers']}** observations with the assumed 1% contamination. These methods answer different questions: SPC measures departures from a smooth precipitation baseline, while LOF identifies locally unusual temperature states or changes. Neither establishes a data error or physical cause.

The reservoir series contains **{len(filling)} weekly observations**. STL reconstruction was verified numerically. The strongest nonzero average spectral frequency is **{frequency[mean_power.argmax()]:.3f} cycles per year**. This describes a frequency component rather than a causal driver. Inspect the decomposition and changes in spectral power alongside the original data.

Regional averaging smooths local extremes, and repeated ERA5 grid cells make sampled points spatially dependent. Results depend on cutoff, neighbours, assumed contamination and smoothing settings; these are exposed in Streamlit for sensitivity analysis."""))''')
md('''## 11. Streamlit integration and Part 2 feedback

The existing Streamlit URL is retained. The Reservoir Data date interval filters overview sparklines, detailed rows and CSV export together. Shared area selection connects reservoir and weather pages. Optional comparisons and separate plots for different units improve readability. New pages provide `st.tabs()` for STL/Spectrogram and SPC/LOF, with user controls, figures and outlier summaries. The existing electricity page, MongoDB secrets handling and NVE API connection remain available. A single-point request is explicit; bulk weather jobs run locally with approval and resumable caching.''')
md('## 12. Development log\n\n'+(ROOT/'reports/DEVELOPMENT_LOG.md').read_text().split('\n',2)[2])
md('## 13. AI usage\n\n'+(ROOT/'reports/AI_USAGE.md').read_text().split('\n',2)[2])
md('''## 14. Submission and sources

Review the development log and geographic assumptions, run this notebook on the complete regional dataset, inspect the PDF export and record the five minute video. The repository must show a merge from the Part 3 development branch into main. Update the existing app rather than creating a new URL. The video link must be accessible to reviewers.

- NVE reservoir source: https://www.nve.no/energi/analyser-og-statistikk/om-magasinstatistikken/
- NVE area metadata: https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOmr%C3%A5der
- Electricity polygons: https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/8
- Administrative polygons: https://gis3.nve.no/map/rest/services/Mapservices/Administrasjon/MapServer/0
- ERA5 API and attribution: https://open-meteo.com/en/docs/historical-weather-api
- API quotas: https://open-meteo.com/en/pricing

The full methodological record is in `reports/ASSUMPTIONS.md`.''')
md("""## Appendix: shared function implementations

These are the actual functions imported and tested above. Printing their source keeps the PDF reviewable without duplicating production logic in the notebook. Their imports and supporting helpers are maintained in the accompanying repository modules. Printing source does not launch any extra downloads.""")
code("""#include the actual reusable implementations in the executed report
import inspect
from src.weather import download_point, download_region
from src.geography import sample_polygon
for function in [sample_polygon, download_point, download_region, spc_analysis, lof_analysis, stl_analysis, spectrogram_analysis]:
    print(function.__name__)
    print(inspect.getsource(function))""")
notebook=nb.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11'}})
path=ROOT/'notebooks/IND320_Project(P3).ipynb'
nb.write(notebook,path);print(path)
