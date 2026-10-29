"""command line tool for the full, resumable 1000 point weather download.

examples (from the project folder):
  python scripts/download_weather.py --estimate              show the quota estimate only
  python scripts/download_weather.py --region NO3 --approved run (or resume) the full download

the download is stopped by the open-meteo quota; run the same command again
later and the cached points are reused.
"""
import argparse
import json
import sys
from pathlib import Path

#make the src package importable when the script is run from any folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.weather import CORE_VARIABLES, VARIABLES, WeatherRateLimit, download_region, estimate_download

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', default='NO3')
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--end', default='2024-12-31')
    parser.add_argument('--approved', action='store_true', help='required for more than one location')
    parser.add_argument('--estimate', action='store_true', help='only print the size and quota estimate')
    parser.add_argument('--core', action='store_true', help='only temperature and precipitation')
    args = parser.parse_args()
    variables = CORE_VARIABLES if args.core else VARIABLES
    print(json.dumps(estimate_download(args.start, args.end, 1000, variables), indent=2), flush=True)
    if not args.estimate:
        try:
            df = download_region(args.region, args.start, args.end, approved=args.approved, variables=variables)
            print(df.describe())
        except WeatherRateLimit as error:
            #exit code 75 means temporary failure: try again later
            print(str(error), file=sys.stderr)
            sys.exit(75)
