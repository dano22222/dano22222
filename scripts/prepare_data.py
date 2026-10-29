"""download the nve polygons and reservoir snapshot used by the notebook (no weather).

python scripts/prepare_data.py            download polygons, sample points, save reservoir data
python scripts/prepare_data.py --saved    rebuild regions and points from the saved polygons
"""
import argparse
import sys
from pathlib import Path

#make the src package importable when the script is run from any folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.geography import prepare_regions
from src.reservoir import ROOT, fetch_reservoir

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--saved', action='store_true', help='reuse data/regions/*.geojson instead of downloading')
    args = parser.parse_args()
    regions = prepare_regions(from_saved=args.saved)
    print(regions[['region']])
    if not args.saved:
        #reservoir snapshot so the notebook gives the same results offline
        df = fetch_reservoir()
        df.to_parquet(ROOT / 'data/reservoir.parquet', index=False)
        print('Reservoir observations:', len(df))
