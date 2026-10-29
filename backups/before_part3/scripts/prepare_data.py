"""Download small official region and reservoir inputs; no weather download."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.geography import prepare_regions
from src.reservoir import fetch_reservoir,ROOT
if __name__=='__main__':
    regions=prepare_regions();print(regions[['region']])
    df=fetch_reservoir();df.to_parquet(ROOT/'data/reservoir.parquet',index=False)
    print('Reservoir observations:',len(df))
