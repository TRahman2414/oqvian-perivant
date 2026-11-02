# Test report

Run date: 2026-11-02

## Automated checks

- Backend: `./scripts/test-backend.sh` — five tests covering loopback ownership, baseline observation, inconclusive probes, R001/R002/R007, evidence, duplicate prevention, notes, status updates, verified-only resolution, DNS/TLS comparisons, approved maintenance, reset, unregistered-port rejection, safe port-conflict handling, and normalized DNS record ordering.
- Frontend: `cd frontend && npm run build` — TypeScript compilation and Vite production bundle.

The Starlette TestClient currently prints a deprecation warning because the installed Starlette release is moving from `httpx` to `httpx2`; it does not fail the test. Do not describe broader production readiness or real external scanning as tested.
