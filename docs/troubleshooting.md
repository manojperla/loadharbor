# Diagnosing a LoadHarbor run

| Symptom | Next check |
|---|---|
| Maven not found | Check PATH/JAVA_HOME or set MAVEN_CMD to the executable, not a shell command. |
| Configuration rejected | Check run.py's ranges and use an integer duration. |
| Nonzero test exit | Read the run's console.log and Gatling assertion report. |
| Partial telemetry | Check summary.json and exporter/event errors; do not use the run as a baseline. |
| Empty dashboard | Check the selected time range, exporter health, and Prometheus scrape status. |
| Live rate falls to zero after a run | Expected when requests stop; cumulative panels and historical samples remain useful. |

Start with `python -m unittest discover -s tests -v`, then
`python run.py --profile smoke`. For monitoring, use the README's Compose setup
and `python ci/verify_monitoring.py`.

The runner accepts duration 1–3600 seconds, arrival rate 0.1–100 users/second,
P95 limits 1–60000 ms, and error limits 0–100 percent. These are input bounds,
not workload recommendations. CLI overrides are recorded in the run summary.

Run one simulation at a time per checkout/exporter so the newest-run selection
does not mix the evidence you are inspecting. Include profile, effective config,
commit SHA, exit status, and telemetry completeness when reporting a regression.
