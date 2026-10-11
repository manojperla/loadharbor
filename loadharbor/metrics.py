"""Read LoadHarbor's own TSV events and expose bounded-cardinality Prometheus metrics."""
import argparse
import math
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, float('inf'))
NAMES = {'catalog', 'product', 'search'}

class Metrics:
    def __init__(self):
        self.requests = defaultdict(int)
        self.latencies = defaultdict(lambda: [0] * len(BUCKETS))
        self.sums = defaultdict(float)
        self.started = 0
        self.active = 0
        self.invalid = 0
    def consume(self, line):
        parts = line.rstrip('\r\n').split('\t')
        try:
            if parts[0] == 'RUN' and len(parts) == 3:
                self.started = int(parts[1]) / 1000; self.active = 1
            elif parts == ['DONE']:
                self.active = 0
            elif parts[0] == 'REQUEST' and len(parts) == 4:
                _, name, raw, status = parts
                duration = int(raw) / 1000
                if name not in NAMES or status not in ('OK', 'KO') or duration < 0:
                    raise ValueError('Invalid request event')
                self.requests[name, status] += 1
                self.sums[name] += duration
                for i, bound in enumerate(BUCKETS):
                    if duration <= bound: self.latencies[name][i] += 1
            else: raise ValueError('Invalid event')
        except (ValueError, IndexError): self.invalid += 1
    def render(self):
        lines = ['# TYPE loadharbor_requests_total counter', '# TYPE loadharbor_response_seconds histogram',
                 '# TYPE loadharbor_run_active gauge', '# TYPE loadharbor_run_start_timestamp_seconds gauge',
                 '# TYPE loadharbor_invalid_events_total counter',
                 f'loadharbor_run_active {self.active}', f'loadharbor_run_start_timestamp_seconds {self.started}',
                 f'loadharbor_invalid_events_total {self.invalid}']
        for name in sorted(NAMES):
            for status in ('OK', 'KO'):
                lines.append(f'loadharbor_requests_total{{request="{name}",status="{status}"}} {self.requests[name,status]}')
            for bound, count in zip(BUCKETS,self.latencies[name]):
                label = '+Inf' if math.isinf(bound) else str(bound)
                lines.append(f'loadharbor_response_seconds_bucket{{request="{name}",le="{label}"}} {count}')
            lines.append(f'loadharbor_response_seconds_count{{request="{name}"}} {self.latencies[name][-1]}')
            lines.append(f'loadharbor_response_seconds_sum{{request="{name}"}} {self.sums[name]}')
        return '\n'.join(lines) + '\n'

class Collector:
    def __init__(self, root, selected=None):
        self.selected=Path(selected) if selected else None
        self.root=Path(root); self.path=None; self.position=0; self.metrics=Metrics(); self.lock=Lock()
    def poll(self):
        files=([self.selected] if self.selected.exists() else []) if self.selected else sorted(self.root.glob('*/events.tsv'))
        if not files: return
        with self.lock:
            if files[-1] != self.path:
                self.path=files[-1]; self.position=0; self.metrics=Metrics()
            with self.path.open(encoding='utf-8') as stream:
                stream.seek(self.position)
                while True:
                    start=stream.tell(); line=stream.readline()
                    if not line.endswith('\n'): stream.seek(start); break
                    self.metrics.consume(line)
                self.position=stream.tell()
    def render(self):
        self.poll()
        with self.lock: return self.metrics.render()

def serve(root, host='127.0.0.1', port=9400):
    collector=Collector(root)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/metrics','/health'):
                self.send_error(404);return
            body=(collector.render() if self.path=='/metrics' else 'ok').encode()
            self.send_response(200);self.send_header('Content-Type','text/plain; version=0.0.4')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer((host,port),Handler)
    Thread(target=server.serve_forever,daemon=True).start()
    return server

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.run/runs');parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=9400)
    args=parser.parse_args();server=serve(args.root,args.host,args.port)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: server.shutdown();server.server_close()
