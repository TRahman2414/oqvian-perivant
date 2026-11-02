# Safety boundaries

- Observation targets come only from the SQLite lab-service registry.
- Lab services bind to `127.0.0.1` and ports in `18080–18099`.
- The observer connects only to registered ports and has short timeouts.
- The demo does not scan customer infrastructure or the public internet.
- A loopback listener is evidence of local lab reachability only.
- No vulnerability, compromise, public exposure, or internet reachability is inferred.
- Timeout and connection failure are recorded as inconclusive/unavailable, not proof of a closed port.
- Remediation is limited to stopping this process's own demo management listener.
- No shell execution, firewall changes, deletion, or destructive actions are exposed.
- Synthetic external snapshots, when implemented, must be distinctly labeled and never passed into live observation logic.
