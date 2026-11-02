# OQVIAN PERIVANT

**See what changed. Find what is exposed. Secure what matters.**

OQVIAN PERIVANT is a local cybersecurity product demonstration for tracking approved assets, observing registered localhost lab services, comparing current state with approved baselines, and opening evidence-backed investigations for changes.

The demo does not scan the internet. It combines actual observations of its own loopback-only test services with clearly labeled synthetic external snapshots. Reachability is not proof of public exposure or vulnerability.

## Current build status

The local showcase includes a React dashboard, fictional inventory, app-owned loopback listeners, persistent observations and investigations, deterministic service rules, synthetic DNS/TLS comparisons, approved maintenance context, investigation notes/status, simulated remediation verification, and presenter reset. This is a local functional demo; it does not scan external targets.

### Run locally

```bash
./scripts/start-demo.sh
```

Open `http://127.0.0.1:4173` for the dashboard and `http://127.0.0.1:8010/docs` for the local API. Stop both processes with Ctrl+C. The database is created as `perivant.db` in the project directory.

Use **Demo control** in the UI to run the four scenarios, verify simulated remediation, or reset. The primary finding can also be replayed with `POST /api/observations/run`, `POST /api/lab/management/start`, and another `POST /api/observations/run`; inspect `GET /api/incidents`.

Run the backend acceptance check with `./scripts/test-backend.sh`.

See [the product context](docs/PRODUCT_CONTEXT.md), [detection rules](docs/DETECTION_RULES.md), [safety boundaries](docs/SAFETY_BOUNDARIES.md), [presenter script](docs/DEMO_SCRIPT.md), and [test report](docs/TEST_REPORT.md). The full project directive is preserved at [MASTER_BUILD_DIRECTIVE.md](docs/MASTER_BUILD_DIRECTIVE.md).
