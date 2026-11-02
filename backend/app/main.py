from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .engine import observe_registered_services
from .lab import HOST, PERMITTED_PORTS, LocalLab
from .models import (
    Asset, AuditEvent, ChangeRequest, Investigation, InvestigationNote,
    LabService, Observation, ObservationRun, Snapshot,
)
from .schemas import CaseUpdate, NoteCreate, SnapshotCompare

lab = LocalLab()
ACTIVE_SCENARIO = "baseline"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_demo(db: Session) -> None:
    if db.scalar(select(Asset.id).limit(1)):
        return
    assets = [
        Asset(name="ASTERGATE-PORTAL-01", category="Customer Portal", criticality="high", owner="Digital Services"),
        Asset(name="ASTERGATE-APP-01", category="Application Server", criticality="medium", owner="Platform Operations"),
        Asset(name="ASTERGATE-BACKUP-01", category="Backup Management", criticality="critical", owner="Infrastructure Security"),
    ]
    db.add_all(assets)
    db.flush()
    db.add_all([
        LabService(asset_id=assets[0].id, name="Customer portal", port=18080, approved=True, kind="baseline"),
        LabService(asset_id=assets[1].id, name="Application API", port=18081, approved=True, kind="baseline"),
        Snapshot(asset_id=assets[0].id, snapshot_type="dns", snapshot_key="portal.astergate.example", source_mode="synthetic_external_snapshot", values={"A": ["192.0.2.10"], "MX": ["mail.astergate.example"]}, scenario_id="baseline"),
        Snapshot(asset_id=assets[0].id, snapshot_type="tls", snapshot_key="portal.astergate.example", source_mode="synthetic_external_snapshot", values={"fingerprint": "8c:11:BASELINE", "subject": "CN=portal.astergate.example", "issuer": "ASTERGATE Demo CA", "valid_from": "2026-10-01", "valid_to": "2027-10-01", "sans": ["portal.astergate.example"]}, scenario_id="baseline"),
        ChangeRequest(asset_id=assets[1].id, title="Approved application maintenance window", approval_status="approved", approved_by="ASTERGATE Change Board", details="Planned service maintenance in the demo scenario.", scenario_id="approved-maintenance"),
    ])
    db.commit()


async def start_baseline_listeners(db: Session) -> None:
    rows = list(db.scalars(select(LabService).where(LabService.kind == "baseline").order_by(LabService.id)))
    for row, name in zip(rows, ("portal", "application")):
        reserved = {p for p in db.scalars(select(LabService.port)) if p != row.port}
        row.port = await lab.start(name, reserved_ports=reserved, preferred_port=row.port)
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo(db)
        await start_baseline_listeners(db)
    yield
    await lab.stop_all()


app = FastAPI(title="OQVIAN PERIVANT API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:4173", "http://localhost:4173"],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type"])


def asset_data(a: Asset) -> dict:
    return {"id": a.id, "name": a.name, "category": a.category, "criticality": a.criticality, "owner": a.owner, "demo": a.demo}


def investigation_data(c: Investigation, db: Session) -> dict:
    asset = db.get(Asset, c.asset_id)
    return {"id": c.id, "title": c.title, "asset": asset.name if asset else "Unknown asset", "asset_id": c.asset_id,
            "status": c.status, "priority": c.priority, "owner": c.owner, "confidence": c.confidence,
            "explanation": c.explanation, "rule_ids": c.rule_ids, "previous_state": c.previous_state,
            "current_state": c.current_state, "host": c.host, "port": c.port, "approved": c.approved,
            "source_mode": c.source_mode, "evidence": c.evidence, "created_at": c.created_at, "updated_at": c.updated_at}


def snapshot_data(s: Snapshot, db: Session) -> dict:
    asset = db.get(Asset, s.asset_id)
    return {"id": s.id, "asset": asset.name if asset else "Unknown asset", "asset_id": s.asset_id,
            "type": s.snapshot_type, "key": s.snapshot_key, "source_mode": s.source_mode,
            "values": s.values, "approved": s.approved, "scenario_id": s.scenario_id, "created_at": s.created_at}


@app.get("/api/health")
def health():
    return {"status": "ok", "product": "OQVIAN PERIVANT", "mode": "local_demo"}


@app.get("/api/system/status")
def system_status():
    return {"product": "OQVIAN PERIVANT", "mode": "local_demo", "backend": "online", "database": "sqlite",
            "listener_host": HOST, "lab_services_running": len(lab.servers), "active_scenario": ACTIVE_SCENARIO,
            "external_scanning": False}


@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    cases = list(db.scalars(select(Investigation)))
    last = db.scalar(select(ObservationRun).order_by(ObservationRun.id.desc()))
    return {"asset_count": len(list(db.scalars(select(Asset)))),
            "open_cases": sum(c.status not in {"resolved", "approved_change"} for c in cases),
            "high_priority": sum(c.priority in {"high", "urgent"} and c.status not in {"resolved", "approved_change"} for c in cases),
            "observed_services": len(list(db.scalars(select(LabService)))),
            "last_observation": last.created_at if last else None,
            "active_scenario": ACTIVE_SCENARIO, "mode_label": "LOCAL LAB + SYNTHETIC SNAPSHOTS"}


@app.get("/api/assets")
def assets(db: Session = Depends(get_db)):
    return [asset_data(a) for a in db.scalars(select(Asset).order_by(Asset.id))]


@app.get("/api/assets/{asset_id}")
def asset_detail(asset_id: int, db: Session = Depends(get_db)):
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    return {**asset_data(a), "services": [service_data(s) for s in db.scalars(select(LabService).where(LabService.asset_id == a.id))],
            "investigations": [investigation_data(c, db) for c in db.scalars(select(Investigation).where(Investigation.asset_id == a.id).order_by(Investigation.created_at.desc()))]}


def service_data(s: LabService) -> dict:
    return {"id": s.id, "asset_id": s.asset_id, "name": s.name, "host": HOST, "port": s.port,
            "protocol": s.protocol, "approved": s.approved, "kind": s.kind, "registered": s.port in PERMITTED_PORTS,
            "running": s.kind in lab.servers and lab.ports.get(s.kind) == s.port or (s.kind == "baseline" and s.port in lab.ports.values())}


@app.get("/api/services")
def services(db: Session = Depends(get_db)):
    return [service_data(s) for s in db.scalars(select(LabService).order_by(LabService.id))]


@app.get("/api/baselines")
def baselines(db: Session = Depends(get_db)):
    return [{"asset": a.name, "owner": a.owner, "criticality": a.criticality,
             "services": [service_data(s) for s in a.services if s.approved]} for a in db.scalars(select(Asset).order_by(Asset.id))]


@app.post("/api/observations/run")
async def run_observation(db: Session = Depends(get_db)):
    try:
        run = await observe_registered_services(db, lab)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rows = list(db.scalars(select(Observation).where(Observation.run_id == run.id)))
    return {"id": run.id, "source_mode": run.source_mode, "created_at": run.created_at,
            "observations": [{"service_id": o.service_id, "host": o.host, "port": o.port, "state": o.state, "evidence": o.evidence} for o in rows]}


@app.get("/api/observations")
def observations(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Observation).order_by(Observation.id.desc()).limit(300)))
    return [{"id": o.id, "run_id": o.run_id, "service_id": o.service_id, "host": o.host, "port": o.port,
             "state": o.state, "evidence": o.evidence, "created_at": o.run.created_at,
             "source_mode": "local_lab_observation"} for o in rows]


@app.get("/api/observations/{observation_id}")
def observation_detail(observation_id: int, db: Session = Depends(get_db)):
    o = db.get(Observation, observation_id)
    if not o:
        raise HTTPException(404, "Observation not found")
    return {"id": o.id, "run_id": o.run_id, "service_id": o.service_id, "host": o.host, "port": o.port,
            "state": o.state, "evidence": o.evidence, "source_mode": "local_lab_observation"}


@app.get("/api/investigations")
@app.get("/api/incidents")
def investigations(db: Session = Depends(get_db)):
    return [investigation_data(c, db) for c in db.scalars(select(Investigation).order_by(Investigation.created_at.desc()))]


@app.get("/api/investigations/{case_id}")
@app.get("/api/incidents/{case_id}")
def investigation_detail(case_id: int, db: Session = Depends(get_db)):
    c = db.get(Investigation, case_id)
    if not c:
        raise HTTPException(404, "Investigation not found")
    notes = list(db.scalars(select(InvestigationNote).where(InvestigationNote.investigation_id == case_id).order_by(InvestigationNote.created_at)))
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "investigation", AuditEvent.entity_id == case_id).order_by(AuditEvent.created_at)))
    return {**investigation_data(c, db), "notes": [{"id": n.id, "author": n.author, "content": n.content, "created_at": n.created_at} for n in notes],
            "timeline": [{"id": e.id, "action": e.action, "actor": e.actor, "previous_state": e.previous_state, "new_state": e.new_state, "created_at": e.created_at} for e in events]}


@app.patch("/api/incidents/{case_id}")
@app.patch("/api/investigations/{case_id}")
def update_investigation(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    c = db.get(Investigation, case_id)
    if not c:
        raise HTTPException(404, "Investigation not found")
    old = {"status": c.status, "owner": c.owner}
    if payload.status is not None:
        if payload.status == "resolved" and c.source_mode == "local_lab_observation" and not db.scalar(
            select(AuditEvent.id).where(AuditEvent.entity_type == "investigation", AuditEvent.entity_id == c.id,
                                        AuditEvent.action == "simulated_remediation_verified")
        ):
            raise HTTPException(409, "Verify the application-owned service is unavailable before resolving this local-lab case")
        c.status = payload.status
    if payload.owner is not None:
        c.owner = payload.owner
    db.add(AuditEvent(entity_type="investigation", entity_id=c.id, action="case_updated", previous_state=str(old), new_state=str({"status": c.status, "owner": c.owner})))
    db.commit()
    db.refresh(c)
    return investigation_data(c, db)


@app.post("/api/incidents/{case_id}/notes")
@app.post("/api/investigations/{case_id}/notes")
def add_note(case_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    c = db.get(Investigation, case_id)
    content = payload.content
    author = payload.author
    if not c:
        raise HTTPException(404, "Investigation not found")
    note = InvestigationNote(investigation_id=c.id, author=author, content=content)
    db.add(note)
    db.add(AuditEvent(entity_type="investigation", entity_id=c.id, action="note_added", new_state=content[:500]))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "author": note.author, "content": note.content, "created_at": note.created_at}


@app.get("/api/findings")
def findings(db: Session = Depends(get_db)):
    return investigations(db)


@app.get("/api/findings/{finding_id}")
def finding_detail(finding_id: int, db: Session = Depends(get_db)):
    return investigation_detail(finding_id, db)


@app.get("/api/changes")
def changes(db: Session = Depends(get_db)):
    return [{"id": c.id, "asset": db.get(Asset, c.asset_id).name, "title": c.title, "approval_status": c.approval_status,
             "approved_by": c.approved_by, "details": c.details, "scenario_id": c.scenario_id, "created_at": c.created_at}
            for c in db.scalars(select(ChangeRequest).order_by(ChangeRequest.id))]


@app.get("/api/changes/{change_id}")
def change_detail(change_id: int, db: Session = Depends(get_db)):
    change = db.get(ChangeRequest, change_id)
    if not change:
        raise HTTPException(404, "Change request not found")
    return {"id": change.id, "asset": db.get(Asset, change.asset_id).name, "title": change.title,
            "approval_status": change.approval_status, "approved_by": change.approved_by,
            "details": change.details, "scenario_id": change.scenario_id, "created_at": change.created_at}


@app.get("/api/snapshots")
def snapshots(db: Session = Depends(get_db)):
    return [snapshot_data(s, db) for s in db.scalars(select(Snapshot).order_by(Snapshot.id.desc()))]


@app.post("/api/snapshots/compare")
def compare_snapshots(payload: SnapshotCompare, db: Session = Depends(get_db)):
    kind = payload.type
    rows = list(db.scalars(select(Snapshot).where(Snapshot.snapshot_type == kind).order_by(Snapshot.id)))
    if len(rows) < 2:
        return {"type": kind, "changed": False, "detail": "Two snapshots are required.", "source_mode": "synthetic_external_snapshot"}
    baseline = next((row for row in rows if row.scenario_id == "baseline" and row.approved), rows[0])
    current = rows[-1]
    before, after = normalize_snapshot(kind, baseline.values), normalize_snapshot(kind, current.values)
    differences = {key: {"before": before.get(key), "after": after.get(key)} for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}
    matched_approval = current.approved or any(ch.approval_status == "approved" and ch.scenario_id == current.scenario_id for ch in db.scalars(select(ChangeRequest).where(ChangeRequest.asset_id == current.asset_id)))
    if differences:
        priority = "informational" if matched_approval else "medium"
        rule_ids = ["R004" if kind == "dns" else "R005"] + ([] if matched_approval else ["R006"])
        fingerprint = f"snapshot:{kind}:{current.snapshot_key}:{current.scenario_id}"
        case = db.scalar(select(Investigation).where(Investigation.fingerprint == fingerprint))
        if not case:
            details = "; ".join(f"{key}: {value['before']} → {value['after']}" for key, value in differences.items())
            case = Investigation(fingerprint=fingerprint, asset_id=current.asset_id,
                title=("DNS configuration changed" if kind == "dns" else "TLS certificate metadata changed"),
                status="approved_change" if matched_approval else "new", priority=priority,
                explanation=("A synthetic configuration snapshot differs from its previous approved snapshot. " + ("A matching fictional approved change is recorded." if matched_approval else "No matching approved change was found; this is a configuration review, not proof of compromise.")),
                rule_ids=rule_ids, previous_state="approved_snapshot", current_state="changed_snapshot", host=current.snapshot_key,
                port=0, approved=matched_approval, source_mode=current.source_mode, evidence=details)
            db.add(case)
        db.add(AuditEvent(entity_type="snapshot", entity_id=current.id, action="snapshot_compared", previous_state=str(before), new_state=str(after)))
        db.commit()
    else:
        db.commit()
    return {"type": kind, "changed": bool(differences), "approved": matched_approval, "differences": differences,
            "source_mode": current.source_mode, "case_id": case.id if differences and case else None,
            "detail": "Synthetic snapshots only; no live DNS lookup or TLS connection was made."}


def normalize_snapshot(kind: str, values: dict) -> dict:
    if kind == "dns":
        return {str(k).upper(): sorted({str(v).strip().lower().rstrip(".") for v in (vals if isinstance(vals, list) else [vals])}) for k, vals in values.items() if k.lower() != "ttl"}
    return {"fingerprint": values.get("fingerprint"), "subject": values.get("subject"), "issuer": values.get("issuer"),
            "valid_from": values.get("valid_from"), "valid_to": values.get("valid_to"), "sans": sorted(set(values.get("sans", [])))}


@app.get("/api/lab/status")
def lab_status(db: Session = Depends(get_db)):
    return {"host": HOST, "allowed_ports": [PERMITTED_PORTS.start, PERMITTED_PORTS.stop - 1], "listeners": services(db), "source_mode": "local_lab_observation"}


@app.post("/api/lab/start")
async def start_lab(db: Session = Depends(get_db)):
    await start_baseline_listeners(db)
    return lab_status(db)


@app.post("/api/lab/stop")
async def stop_lab():
    await lab.stop_all()
    return {"status": "stopped", "detail": "Only OQVIAN PERIVANT application-owned listeners were stopped."}


@app.post("/api/lab/management/start")
async def start_management(db: Session = Depends(get_db)):
    service = db.scalar(select(LabService).where(LabService.kind == "management"))
    if service:
        if "management" not in lab.servers:
            reserved = {p for p in db.scalars(select(LabService.port)) if p != service.port}
            service.port = await lab.start("management", reserved_ports=reserved, preferred_port=service.port)
            db.commit()
        return {"status": "running", "host": HOST, "port": service.port, "approved": False}
    reserved = set(db.scalars(select(LabService.port)))
    port = await lab.start("management", reserved_ports=reserved)
    asset = db.scalar(select(Asset).where(Asset.name == "ASTERGATE-BACKUP-01"))
    service = LabService(asset_id=asset.id, name="Backup management interface", port=port, approved=False, kind="management")
    db.add(service)
    db.commit()
    db.refresh(service)
    return {"status": "running", "host": HOST, "port": port, "approved": False, "source_mode": "local_lab_observation"}


@app.post("/api/lab/management/stop")
async def stop_management(db: Session = Depends(get_db)):
    service = db.scalar(select(LabService).where(LabService.kind == "management"))
    if not service:
        return {"status": "stopped", "detail": "No demo management service is registered."}
    await lab.stop("management")
    return {"status": "stopped", "port": service.port, "detail": "Only the application-owned loopback listener was stopped."}


@app.get("/api/demo/scenarios")
def demo_scenarios():
    return {"active": ACTIVE_SCENARIO, "scenarios": [
        {"id": "management-exposure", "title": "Unexpected management service", "mode": "local_lab_observation"},
        {"id": "dns-drift", "title": "DNS configuration drift", "mode": "synthetic_external_snapshot"},
        {"id": "tls-change", "title": "TLS certificate metadata change", "mode": "synthetic_external_snapshot"},
        {"id": "approved-maintenance", "title": "Approved maintenance", "mode": "local_lab_observation"},
    ]}


@app.post("/api/demo/scenarios/{scenario_id}/run")
async def run_scenario(scenario_id: str, db: Session = Depends(get_db)):
    global ACTIVE_SCENARIO
    valid = {"management-exposure", "dns-drift", "tls-change", "approved-maintenance"}
    if scenario_id not in valid:
        raise HTTPException(404, "Unknown demo scenario")
    ACTIVE_SCENARIO = scenario_id
    if scenario_id == "management-exposure":
        await start_management(db)
        result = await run_observation(db)
        return {"scenario": scenario_id, "message": "Started the application-owned localhost management listener and observed registered lab services.", "result": result}
    if scenario_id in {"dns-drift", "tls-change"}:
        kind = "dns" if scenario_id == "dns-drift" else "tls"
        asset = db.scalar(select(Asset).where(Asset.name == "ASTERGATE-PORTAL-01"))
        existing = list(db.scalars(select(Snapshot).where(Snapshot.snapshot_type == kind).order_by(Snapshot.id)))
        baseline = existing[0]
        if kind == "dns":
            changed_values = {**baseline.values, "A": ["198.51.100.20"]}
        else:
            changed_values = {**baseline.values, "fingerprint": "A7:42:RENEWED", "valid_to": "2027-11-15"}
        db.add(Snapshot(asset_id=asset.id, snapshot_type=kind, snapshot_key=baseline.snapshot_key,
                        source_mode="synthetic_external_snapshot", values=changed_values, approved=False, scenario_id=scenario_id))
        db.commit()
        compared = compare_snapshots(SnapshotCompare(type=kind), db)
        return {"scenario": scenario_id, "message": "Compared labeled synthetic snapshots; no network request was made.", "result": compared}
    # Approved maintenance adds a harmless app-owned local service with explicit recorded approval.
    service = db.scalar(select(LabService).where(LabService.kind == "maintenance"))
    asset = db.scalar(select(Asset).where(Asset.name == "ASTERGATE-APP-01"))
    if not service:
        reserved = set(db.scalars(select(LabService.port)))
        port = await lab.start("maintenance", reserved_ports=reserved)
        service = LabService(asset_id=asset.id, name="Approved maintenance endpoint", port=port, approved=True, kind="maintenance")
        db.add(service)
        db.add(ChangeRequest(asset_id=asset.id, title="Approved demo maintenance endpoint", approval_status="approved", approved_by="ASTERGATE Change Board", details="Approval explicitly matches the demo maintenance scenario.", scenario_id=scenario_id))
        db.commit()
    result = await run_observation(db)
    return {"scenario": scenario_id, "message": "Observed an approved local change; it is recorded with approval evidence and should not create an urgent case.", "result": result}


@app.post("/api/demo/remediate")
async def remediate(db: Session = Depends(get_db)):
    service = db.scalar(select(LabService).where(LabService.kind == "management"))
    if not service:
        raise HTTPException(409, "Run the management-service scenario first")
    await lab.stop("management")
    run = await observe_registered_services(db, lab)
    row = db.scalar(select(Observation).where(Observation.run_id == run.id, Observation.service_id == service.id))
    if not row or row.state != "unavailable":
        raise HTTPException(409, "Remediation verification is inconclusive; case remains open")
    cases = list(db.scalars(select(Investigation).where(Investigation.port == service.port, Investigation.status != "resolved")))
    for case in cases:
        case.status = "resolved"
        case.explanation += " Simulated remediation was verified by a fresh loopback observation showing the demo listener unavailable."
        case.current_state = "unavailable"
        case.evidence += f" Verification observation {run.id}: {row.evidence}"
        db.add(AuditEvent(entity_type="investigation", entity_id=case.id, action="simulated_remediation_verified", previous_state="open", new_state="resolved"))
    db.commit()
    return {"status": "verified", "source_mode": "local_lab_observation", "observation_run_id": run.id, "verified_state": row.state,
            "detail": "Only the application-owned loopback listener was stopped; the service is unavailable on the follow-up observation."}


@app.post("/api/demo/reset")
async def reset_demo():
    global ACTIVE_SCENARIO
    await lab.stop_all()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo(db)
        await start_baseline_listeners(db)
    ACTIVE_SCENARIO = "baseline"
    return {"status": "reset", "active_scenario": ACTIVE_SCENARIO, "detail": "Demo records and synthetic fixtures were restored; only app-owned listeners were managed."}
