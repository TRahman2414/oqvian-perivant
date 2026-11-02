# OQVIAN PERIVANT build rules

## Project identity

- Product name: OQVIAN PERIVANT.
- Keep all UI, docs, sample data, and demo labels under OQVIAN branding.
- The project is a functional local demonstration, not a production scanner.

## Safety boundary

- Network listeners and observations may target only application-owned services bound to `127.0.0.1`.
- Reject non-loopback targets and ports outside the explicit lab registry.
- Never contact external or fictional documentation addresses.
- Label data as local lab observation, synthetic external snapshot, approved configuration, detected configuration change, or simulated remediation.
- Do not call a localhost service publicly exposed or infer vulnerability from TCP reachability.
- Keep remediation simulated and reversible. Do not add firewall changes, deletion, or arbitrary command execution.

## Agent ownership

- Codex owns backend, safety checks, database, observation, comparison, detection, API integration, and final review.
- Antigravity owns `frontend/` design and implementation only.
- OpenCode may own seed data or documentation only when explicitly assigned a bounded task.
- Kilo may perform a no-edit review or focused unit-test task; it has no live push adapter, so invoke it through its CLI and relay its result.
- Do not have two agents edit the same files. Codex reviews all delegated changes before integrating them.

## Product constraints

- Local Linux deployment; no paid APIs, GPU, cloud services, live customer notifications, or real external scans.
- Use the documented fictional ASTERGATE CLOUD SERVICES inventory and `.example` names.
- Keep source-mode and evidence data explicit in APIs and UI.
- Prefer simple deterministic rules over AI-generated conclusions.
- Read `docs/MASTER_BUILD_DIRECTIVE.md` for full scope and acceptance criteria.
