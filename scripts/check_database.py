"""Read only verification of the existing Part 2 MongoDB source."""
import argparse,os,json
from pathlib import Path
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--env',type=Path,default=ROOT/'.env');args=parser.parse_args()
load_dotenv(args.env)
client=MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=15000,tlsCAFile=certifi.where())
client.admin.command('ping')
c=client['ind320']['cross_border_flows']
print(json.dumps({'connection_ok':True,'documents':c.estimated_document_count(),
 'connections':c.distinct('connection'),'years':c.distinct('year')},indent=2))
client.close()
