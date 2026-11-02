# Detection rules

- **R001 — Newly reachable unapproved service:** a registered, previously unavailable loopback service becomes reachable and is not approved.
- **R002 — Unapproved service:** a registered unapproved service is reachable, independently of whether it is newly reachable.
- **R003 — Approved service unavailable:** a previously reachable approved local service returns a connection refusal. Timeouts are inconclusive and do not trigger this rule.
- **R004 — DNS configuration change:** normalized synthetic DNS record sets differ from the approved baseline.
- **R005 — TLS metadata change:** synthetic certificate fingerprint or metadata differs from its approved baseline.
- **R006 — Missing change approval:** a snapshot change has no matching approved fictional change record.
- **R007 — Management service review:** an unapproved management listener is reachable. Higher asset criticality raises the review priority.

Priority labels are deterministic demo policy, not attack probability. Local reachability does not establish public exposure or vulnerability. Synthetic snapshot changes do not prove DNS compromise or certificate misuse.
