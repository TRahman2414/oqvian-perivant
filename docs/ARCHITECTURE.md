# Architecture

The demo uses one FastAPI process, SQLAlchemy with SQLite, and application-owned asyncio listeners. The API, database, and lab listeners bind to loopback. No external DNS, TLS, or network observation is performed in the first milestone.

Observation runs persist each registered service's host, port, state, timestamp, evidence, and source mode. The comparison engine compares against the previous run, then applies deterministic R001 (newly reachable) and R002 (not approved) rules. An active finding fingerprint prevents repeated runs from duplicating the same case.

The management listener is inert and serves a fixed local demo response. Start and stop actions operate only on the listener held by the process. Failure or timeout remains inconclusive and is not treated as confirmed closed.
