# LoadHarbor

**Gatling Java simulations · Python orchestration · Prometheus · Grafana**

A runnable performance-testing reference project by Manoj Perla. Java defines load
and assertions; Python starts the demo API, launches Maven, preserves its exit status,
and exposes simulation telemetry for Grafana. Python uses only the standard library.

## Run a test

Install JDK 17, Maven 3.9+, and Python 3.12+. From this repository:

```sh
python -m unittest discover -s tests -v
python run.py --profile smoke
```

The demo binds only to localhost on a random port and shuts down automatically.
No account, secret, Docker, or external test website is required for this command.
Set `JAVA_HOME` and add Maven to PATH; alternatively set `MAVEN_CMD` to the Maven
executable (on Windows, the full path to `mvn.cmd`). Paths containing spaces work.

If Windows JDK 17 reports `Unable to establish loopback connection` with a
`UnixDomainSockets.connect` stack trace, use this PowerShell workaround for the
current terminal, then rerun the command:

```powershell
$env:JAVA_TOOL_OPTIONS='-Djdk.net.unixdomain.tmpdir=target/tcp-fallback'
```

Keep that directory absent so Java falls back to TCP loopback. This workaround
was needed on the development machine; Linux CI does not require it.

## Grafana dashboard

Install Docker with Compose, then:

```sh
docker compose up -d --build
python run.py --profile baseline
python ci/verify_monitoring.py
```

Open http://localhost:3000/d/loadharbor. Local demo login: `admin` /
`loadharbor-local-demo`. Override `GRAFANA_ADMIN_PASSWORD` before first startup for a
different password. The monitoring ports bind only to localhost. These are local
demo settings, not an internet-facing Grafana deployment.

The dashboard is provisioned automatically: total requests, error percentage,
P95 latency, run activity, request throughput, P50/P90/P95 trends, request outcomes,
and exporter health. Prometheus scrapes the Python exporter every two seconds.
After a run finishes the cumulative panels remain populated; live rate charts
fall to zero. Select the time range covering the run to view its trend.

`docker compose down` stops services and retains history in Docker volumes.
`python -m loadharbor.metrics` can expose metrics without Docker on port 9400.
The exporter selects the newest run, resets its counters between runs, and avoids
unbounded run-ID labels. Prometheus retains earlier samples. Run tests sequentially
in a checkout; simultaneous runs need separate output directories/exporters.

## Workloads and thresholds

| Profile | Injection | Duration | Users per second | P95 limit | Error limit |
|---|---|---:|---:|---:|---:|
| smoke | constant arrivals | 10 s | 1 | 1000 ms | 1% |
| baseline | constant arrivals | 30 s | 3 | 750 ms | 1% |
| load | constant arrivals | 60 s | 10 | 750 ms | 1% |
| stress | ramp arrivals | 60 s | 1 → 20 | 1000 ms | 1% |

Each user browses catalog → product → search with short pauses. Arrival rate is
users/sec, not concurrent users or requests/sec. Thresholds are demo defaults,
not production SLO recommendations. Configure `config/profiles.json`, or use
`--duration`, `--rate`, `--p95-ms`, and `--max-error-percent`. Gatling assertions
fail the Maven command and Python runner when thresholds are exceeded.

To test your own dedicated environment, adapt routes and checks in
`CatalogSimulation.java`, then explicitly pass `--base-url https://your-test-host`.
Only load-test targets you control or have permission to test. The default demo
results demonstrate the framework, not the capacity of a production service.

## Results and integration details

- Gatling's official HTML reports: `target/gatling/<run>/index.html`.
- Per-run console log, summary JSON, custom event stream, and metrics snapshot:
  `.run/runs/<run>/`.
- Grafana latency percentiles are histogram estimates. Gatling's report and native
  assertions remain authoritative for pass/fail.
- The Java simulation uses the supported `responseTimeInMillis` check and session
  state to emit our own versioned-by-source TSV events. It does **not** parse Gatling's
  internal `simulation.log`. Transport failures use elapsed wall time as a fallback.
- A bounded asynchronous queue keeps disk writes off Gatling's request path. Queue
  overflow or writer failure fails the run. Extra instrumentation still adds some
  load-generator overhead; validate generator capacity before scaling tests.
- Request names are fixed (catalog/product/search), avoiding sensitive URLs, response
  bodies, credentials, or high-cardinality labels in telemetry.

The GitHub Actions workflow runs Python tests, a Gatling smoke test, and the complete
monitoring stack. It verifies real Prometheus samples and Grafana datasource/dashboard
availability, then uploads results. It does not load-test your public portfolio.

## Structure

`src/test/java`: Gatling simulation and telemetry; `loadharbor`: Python demo/exporter;
`run.py`: orchestration; `monitoring`: provisioned Grafana and Prometheus configuration;
`tests`: exporter edge cases; `.github/workflows`: CI.

References: [Gatling Java SDK](https://docs.gatling.io/tutorials/test-as-code/java-jvm/installation-guide/),
[Gatling checks](https://docs.gatling.io/concepts/checks/),
[Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/).
Project source is MIT licensed. Gatling and its Highcharts reports retain their
respective upstream licenses; this repository does not redistribute their binaries.
