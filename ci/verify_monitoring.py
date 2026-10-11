import base64,json,os,time
from urllib.request import Request,urlopen
from urllib.parse import urlencode

def get(url,auth=False):
    headers={}
    if auth:
        token=base64.b64encode(('admin:'+os.environ.get('GRAFANA_ADMIN_PASSWORD','loadharbor-local-demo')).encode()).decode()
        headers['Authorization']='Basic '+token
    with urlopen(Request(url,headers=headers),timeout=5) as r:return json.load(r)

deadline=time.monotonic()+90
while True:
    try:
        query=get('http://127.0.0.1:9090/api/v1/query?'+urlencode({'query':'sum(loadharbor_requests_total)'}))
        total=float(query['data']['result'][0]['value'][1])
        dashboard=get('http://127.0.0.1:3000/api/dashboards/uid/loadharbor',True)
        datasource=get('http://127.0.0.1:3000/api/datasources/uid/loadharbor-prometheus/health',True)
        assert total>0 and len(dashboard['dashboard']['panels'])==8 and datasource['status']=='OK'
        print(f'Prometheus has {total:g} requests; Grafana dashboard has 8 panels and a healthy datasource.');break
    except Exception:
        if time.monotonic()>deadline:raise
        time.sleep(2)
