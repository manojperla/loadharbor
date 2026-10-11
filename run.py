"""Python orchestration for Gatling Java simulations; no third-party Python packages."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit
from loadharbor.demo import start_demo
from loadharbor.metrics import Collector

ROOT=Path(__file__).resolve().parent
def validate(config):
    ranges={'duration':(1,3600),'rate':(0.1,100),'p95Ms':(1,60000),'maxErrorPercent':(0,100)}
    for key,(low,high) in ranges.items():
        if not low <= config[key] <= high: raise ValueError(f'{key} must be between {low} and {high}')
    if int(config['duration']) != config['duration']: raise ValueError('duration must be an integer')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['smoke','baseline','load','stress'],default='smoke')
    parser.add_argument('--base-url',help='Explicit dedicated test target implementing the demo routes; omitted starts a local demo')
    parser.add_argument('--duration',type=int);parser.add_argument('--rate',type=float)
    parser.add_argument('--p95-ms',type=int);parser.add_argument('--max-error-percent',type=float)
    args=parser.parse_args()
    config=json.loads((ROOT/'config/profiles.json').read_text())[args.profile]
    for field,key in [('duration','duration'),('rate','rate'),('p95_ms','p95Ms'),('max_error_percent','maxErrorPercent')]:
        value=getattr(args,field)
        if value is not None: config[key]=value
    validate(config)
    maven=os.environ.get('MAVEN_CMD') or shutil.which('mvn.cmd' if os.name=='nt' else 'mvn')
    if not maven: raise RuntimeError('Install Maven 3.9+ and JDK 17; or set MAVEN_CMD to the Maven executable')
    demo=None
    if args.base_url:
        parsed=urlsplit(args.base_url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.query or parsed.fragment: raise ValueError('Use an HTTP(S) base URL without credentials, query or fragment')
        base=args.base_url.rstrip('/')
    else:
        demo=start_demo();base=f'http://127.0.0.1:{demo.server_port}'
    run_id=f'{time.time_ns()}-{uuid.uuid4().hex[:8]}'
    out=ROOT/'.run/runs'/run_id;out.mkdir(parents=True)
    command=[maven,'--batch-mode','--no-transfer-progress','gatling:test',f'-DbaseUrl={base}',f'-Dprofile={args.profile}',f'-Dtelemetry={(out / "events.tsv").relative_to(ROOT).as_posix()}',*[f'-D{k}={v}' for k,v in config.items()]]
    code=1
    try:
        with (out/'console.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
            try:
                for line in process.stdout: print(line,end='');log.write(line)
                code=process.wait()
            except KeyboardInterrupt:
                process.terminate();process.wait(timeout=15);raise
        collector=Collector(ROOT/'.run/runs', selected=out/'events.tsv'); metrics=collector.render()
        (out/'metrics.prom').write_text(metrics,encoding='utf-8')
        m=collector.metrics;count=sum(m.requests.values())
        complete=bool(count) and not m.active and not m.invalid
        if not complete: code=code or 1
        summary={'profile':args.profile,'config':config,'requests':count,'errors':sum(n for (name,status),n in m.requests.items() if status=='KO'),'telemetry_complete':complete,'exit_code':code}
        (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(f'\nLoadHarbor results: {out}\nGatling HTML reports: {ROOT / "target/gatling"}')
        return code
    finally:
        if demo: demo.shutdown();demo.server_close()

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,RuntimeError,OSError) as error: print(f'LoadHarbor: {error}',file=sys.stderr);sys.exit(2)
