"""list official nve layers likely to contain regional statistical boundaries."""
import requests
from concurrent.futures import ThreadPoolExecutor
base='https://gis3.nve.no/map/rest/services/'
services=requests.get(base+'Mapservices',params={'f':'json'},timeout=60).json()['services']
def inspect(service):
    try:
        data=requests.get(base+service['name']+'/MapServer',params={'f':'json'},timeout=45).json()
        return [(service['name'],x['id'],x['name']) for x in data.get('layers',[])
                if any(w in x['name'].lower() for w in ['nedbørom','nedborom','tilsig','magasin','elspot','statistikk','region'])]
    except requests.RequestException:return []
with ThreadPoolExecutor(max_workers=6) as pool:
    for found in pool.map(inspect,services):
        for row in found:print(row)
