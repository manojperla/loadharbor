import tempfile
import unittest
from pathlib import Path
from loadharbor.metrics import Metrics, Collector
from run import validate

class MetricsTests(unittest.TestCase):
    def test_success_and_failure_metrics(self):
        m=Metrics();m.consume('RUN\t1000\tsmoke\n');m.consume('REQUEST\tcatalog\t25\tOK\n');m.consume('REQUEST\tcatalog\t100\tKO\n');m.consume('DONE\n')
        self.assertEqual(m.requests['catalog','OK'],1);self.assertEqual(m.requests['catalog','KO'],1)
        self.assertIn('loadharbor_response_seconds_bucket{request="catalog",le="0.025"} 1',m.render())
        self.assertIn('loadharbor_response_seconds_count{request="catalog"} 2',m.render());self.assertEqual(m.active,0)
    def test_invalid_events_do_not_corrupt_metrics(self):
        m=Metrics()
        for line in ['REQUEST\tbad-name\t20\tOK','REQUEST\tcatalog\t-1\tOK','REQUEST\tcatalog\tx\tOK','unexpected'] : m.consume(line)
        self.assertEqual(m.invalid,4);self.assertEqual(sum(m.requests.values()),0)
    def test_partial_lines_wait_and_repeated_scrapes_do_not_double_count(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'001/events.tsv';p.parent.mkdir();p.write_text('RUN\t1000\tsmoke\nREQUEST\tcatalog\t20')
            c=Collector(folder);c.poll();self.assertEqual(sum(c.metrics.requests.values()),0)
            with p.open('a') as stream:stream.write('\tOK\nDONE\n')
            c.poll();c.poll();self.assertEqual(sum(c.metrics.requests.values()),1)
    def test_new_run_resets_latest_counters(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ['001','002']:
                p=Path(folder)/name/'events.tsv';p.parent.mkdir();p.write_text('RUN\t2000\tsmoke\nREQUEST\tproduct\t10\tOK\nDONE\n')
            c=Collector(folder);c.poll();self.assertEqual(sum(c.metrics.requests.values()),1);self.assertEqual(c.path.parent.name,'002')
    def test_rejects_invalid_load_configuration(self):
        with self.assertRaises(ValueError):validate({'duration':10,'rate':float('nan'),'p95Ms':1000,'maxErrorPercent':1})
        with self.assertRaises(ValueError):validate({'duration':10,'rate':101,'p95Ms':1000,'maxErrorPercent':1})

    def test_missing_selected_run_does_not_reuse_old_results(self):
        with tempfile.TemporaryDirectory() as folder:
            old=Path(folder)/'001/events.tsv';old.parent.mkdir()
            old.write_text('RUN\t1000\tsmoke\nREQUEST\tcatalog\t20\tOK\nDONE\n')
            c=Collector(folder, selected=Path(folder)/'002/events.tsv')
            c.render()
            self.assertEqual(sum(c.metrics.requests.values()),0)

if __name__=='__main__':unittest.main()
