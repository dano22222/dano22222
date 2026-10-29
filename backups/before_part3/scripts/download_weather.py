"""Explicit CLI for approved, resumable weather downloads."""
import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.weather import download_region,estimate_download,WeatherRateLimit
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--region',default='NO3');p.add_argument('--start',default='2024-01-01');p.add_argument('--end',default='2024-12-31');p.add_argument('--approved',action='store_true');p.add_argument('--pilot',action='store_true');p.add_argument('--estimate',action='store_true');a=p.parse_args()
 print(json.dumps(estimate_download(a.start,a.end,1 if a.pilot else 1000),indent=2),flush=True)
 if not a.estimate:
  try:df=download_region(a.region,a.start,a.end,approved=a.approved,max_points=1 if a.pilot else None);print(df.describe())
  except WeatherRateLimit as e:print(str(e),file=sys.stderr);sys.exit(75)
