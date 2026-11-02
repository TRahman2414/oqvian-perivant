# Presenter script (5–7 minutes)

1. Open Overview and explain the fictional ASTERGATE inventory and source labels.
2. Run an observation to show the two approved, app-owned localhost services.
3. In Demo Control, run **Unexpected management service**. The scenario starts a local-only listener and observes it.
4. Open the generated investigation. Show its previous/current state, rules, local evidence, fictional asset owner, and approval status.
5. Add a short analyst note and acknowledge the case.
6. Choose **Simulate remediation and verify**. PERIVANT stops only its own listener, performs a fresh local observation, and resolves the case only when that listener is confirmed unavailable.
7. Run DNS and TLS scenarios to show synthetic before/after comparisons and their labels.
8. Run Approved maintenance to show that an explicitly approved local change is recorded without an urgent case.
9. Use Reset demo to return the environment to its starting state.

Explain that this is a functional local demo. Do not describe it as live public internet monitoring or claim that localhost evidence establishes internet exposure.
