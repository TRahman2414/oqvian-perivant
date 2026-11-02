import asyncio
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from .lab import HOST, PERMITTED_PORTS, LocalLab
from .models import Asset, AuditEvent, Investigation, LabService, Observation, ObservationRun


async def observe_registered_services(db: Session, lab: LocalLab) -> ObservationRun:
    services = list(db.scalars(select(LabService).order_by(LabService.id)))
    if any(s.port not in PERMITTED_PORTS for s in services):
        raise ValueError("Observation target is outside the registered loopback lab")
    run = ObservationRun(source_mode="local_lab_observation")
    db.add(run)
    db.flush()

    def lab_key(service: LabService) -> str:
        if service.kind == "baseline":
            return {"Customer portal": "portal", "Application API": "application"}.get(service.name, "")
        return service.kind

    async def check(service: LabService) -> tuple[LabService, str, str]:
        key = lab_key(service)
        if not key or lab.ports.get(key) != service.port or key not in lab.servers:
            return service, "unavailable", f"Registered application-owned listener {HOST}:{service.port} is not running; no connection was made to another process."
        writer = None
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(HOST, service.port), timeout=0.6)
            token = lab.tokens[key]
            writer.write(f"GET /health?probe={token} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode())
            await writer.drain()
            response = await asyncio.wait_for(reader.read(512), timeout=0.6)
            if not response.startswith(b"HTTP/1.1 200") or token.encode() not in response:
                return service, "inconclusive", f"The application-owned listener {HOST}:{service.port} did not confirm its private lab probe token."
            return service, "reachable", f"Authenticated health response from application-owned listener {HOST}:{service.port} succeeded."
        except ConnectionRefusedError:
            return service, "unavailable", f"Connection refused by registered application-owned listener {HOST}:{service.port}; this result describes local lab reachability only."
        except asyncio.TimeoutError:
            return service, "inconclusive", f"Timed out while checking registered local listener {HOST}:{service.port}; a timeout does not prove that the service is closed."
        except OSError as exc:
            return service, "inconclusive", f"Local observation failed for {HOST}:{service.port}: {type(exc).__name__}; the state is inconclusive."
        finally:
            if writer:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass

    # The inventory is deliberately small; the semaphore keeps future fixtures bounded.
    semaphore = asyncio.Semaphore(4)

    async def bounded_check(service: LabService):
        async with semaphore:
            return await check(service)

    results = await asyncio.gather(*(bounded_check(s) for s in services))
    run_ids = list(db.scalars(select(ObservationRun.id).where(ObservationRun.id < run.id).order_by(ObservationRun.id.desc()).limit(100)))
    prior_by_port: dict[int, str] = {}
    for old_id in run_ids:
        if len(prior_by_port) == len(services):
            break
        for old in db.scalars(select(Observation).where(Observation.run_id == old_id)):
            if old.state in {"reachable", "unavailable"} and old.port not in prior_by_port:
                prior_by_port[old.port] = old.state
    has_prior_runs = bool(run_ids)

    for service, state, evidence in results:
        prior = prior_by_port.get(service.port, "unavailable" if has_prior_runs else "not_observed")
        db.add(Observation(run_id=run.id, service_id=service.id, host=HOST, port=service.port, state=state, evidence=evidence))
        asset = db.get(Asset, service.asset_id)
        if state == "inconclusive":
            continue

        rules: list[str] = []
        if state == "reachable" and not service.approved and prior in {"not_observed", "unavailable"} and prior != "not_observed":
            rules.append("R001")
        if state == "reachable" and not service.approved:
            rules.append("R002")
        if state == "reachable" and not service.approved and service.kind == "management":
            rules.append("R007")
        if state == "unavailable" and prior == "reachable" and service.approved:
            rules.append("R003")
        if not rules:
            continue

        category = "unapproved-service" if not service.approved else ("service-unavailable" if "R003" in rules else "newly-reachable")
        fingerprint = hashlib.sha256(f"{service.id}:{service.port}:{category}".encode()).hexdigest()[:32]
        case = db.scalar(select(Investigation).where(Investigation.fingerprint == fingerprint))
        critical = bool(asset and asset.criticality.lower() in {"critical", "high"})
        if "R007" in rules and critical:
            priority = "high"
        elif "R002" in rules or "R001" in rules:
            priority = "high" if critical else "medium"
        else:
            priority = "medium"
        explanation = (
            f"A registered service on {HOST} changed from {prior} to {state}. "
            f"The fictional asset {asset.name if asset else service.asset_id} has {asset.criticality if asset else 'unknown'} criticality. "
            "This is local lab evidence only; it does not establish internet exposure, compromise, or vulnerability."
        )
        if case:
            if case.status == "resolved" and state == "reachable":
                case.status = "reopened"
            case.current_state = state
            case.updated_at = run.created_at
            case.explanation = explanation
            case.evidence += f"\nObservation run {run.id}: {evidence}"
            case.rule_ids = sorted(set(case.rule_ids + rules))
            db.add(AuditEvent(entity_type="investigation", entity_id=case.id, action="condition_reobserved", previous_state=prior, new_state=state))
        else:
            title = {
                "R001": f"Newly reachable service: {service.name}",
                "R002": f"Unapproved service: {service.name}",
                "R003": f"Approved service unavailable: {service.name}",
                "R007": f"Management service requires review: {service.name}",
            }.get(rules[0], f"Service change: {service.name}")
            db.add(Investigation(
                fingerprint=fingerprint, asset_id=service.asset_id, title=title,
                status="new", priority=priority, owner=asset.owner if asset else "Unassigned",
                explanation=explanation, rule_ids=rules, previous_state=prior, current_state=state,
                host=HOST, port=service.port, approved=service.approved,
                source_mode=run.source_mode, evidence=f"Previous observation: {prior}. Current observation: {state}. {evidence}",
            ))
    db.commit()
    db.refresh(run)
    return run
