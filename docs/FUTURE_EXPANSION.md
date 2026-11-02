# Future expansion

Possible next steps after the showcase include persistent organization and baseline versioning, stronger audit retention, analyst authentication, role-based access, import/export for approved asset inventories, and an optional adapter for explicitly authorized customer-controlled domains.

Any future live adapter must require explicit target ownership and scope approval, remain read-only by default, preserve source provenance, enforce rate and concurrency limits, and be separately tested. DNS or TLS observations must never turn `.example` fixtures into live lookups. Production use also needs deployment hardening, migrations, access control, backup/restore, retention policy, and security review; none are implied by this demo.
