"""resume an approved download after the provider's hourly quota resets"""
import argparse,sys,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.weather import download_region,WeatherRateLimit
parser=argparse.ArgumentParser()
parser.add_argument('--approved',action='store_true',required=True)
parser.add_argument('--max-hours',type=float,default=7)
parser.add_argument('--wait-next-hour',action='store_true')
args=parser.parse_args();deadline=time.monotonic()+args.max_hours*3600

def wait_next_hour():
    now=datetime.now(timezone.utc)
    target=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1,minutes=1)
    print('respecting hourly quota; next attempt:',target.isoformat(),flush=True)
    while datetime.now(timezone.utc)<target:
        if time.monotonic()>=deadline:raise TimeoutError('approved retry window ended')
        time.sleep(min(30,max(.1,(target-datetime.now(timezone.utc)).total_seconds())))

if args.wait_next_hour:wait_next_hour()
while time.monotonic()<deadline:
    try:
        result=download_region('NO3','2024-01-01','2024-12-31',approved=args.approved)
        print('complete regional mean:',result.shape,flush=True)
        break
    except WeatherRateLimit as error:
        print(error,flush=True)
        if 'daily' in str(error).lower():raise
        wait_next_hour()
    except requests.RequestException as error:
        print('temporary network error:',type(error).__name__,flush=True)
        for _ in range(2):time.sleep(30)
else:raise TimeoutError('approved retry window ended')
