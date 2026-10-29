"""verify the completed spatial mean against all cached point series"""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.weather import ROOT,WEATHER_DIR,load_region,validate_hourly,VARIABLES

def audit(region='NO3',start='2024-01-01',end='2024-12-31'):
    mean,metadata=load_region(region,start,end)
    folder=WEATHER_DIR/metadata['point_cache']
    files=sorted(folder.glob('point_*.parquet'))
    if len(files)!=1000:raise ValueError('need exactly 1000 cached point files')
    total=np.zeros_like(mean[VARIABLES].to_numpy(),dtype='float64')
    cells=set()
    for path in files:
        point=validate_hourly(pd.read_parquet(path),start,end)
        total+=point[VARIABLES].to_numpy()
        meta=json.loads(path.with_suffix('.json').read_text())
        if meta['model']!='era5':raise ValueError('unexpected model')
        cells.add((meta['latitude'],meta['longitude']))
    error=float(np.max(np.abs(total/1000-mean[VARIABLES].to_numpy())))
    if error>1e-10:raise ValueError('regional mean does not equal the pointwise average')
    report={'region':region,'points':1000,'hours':len(mean),'point_hours':1000*len(mean),
       'scalar_values':1000*len(mean)*2,'missing_values':int(mean.isna().sum().sum()),
       'unique_returned_grid_cells':len(cells),'max_recomputed_mean_error':error,
       'temperature_range_c':[float(mean.temperature_2m.min()),float(mean.temperature_2m.max())],
       'precipitation_range_mm_h':[float(mean.precipitation.min()),float(mean.precipitation.max())],
       'mean_annual_precipitation_mm':float(mean.precipitation.sum()),
       'note':'sampled points sharing era5 cells are spatially dependent; temperature can also be elevation adjusted by the provider'}
    (ROOT/'reports/weather_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2));return report
if __name__=='__main__':audit()
