import asyncio
import socket

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import DB_PATH, SessionLocal
from app.lab import PERMITTED_PORTS, LocalLab
from app.main import app, lab
from app.models import Asset, LabService, Observation


def test_unapproved_management_service_creates_evidence_backed_case():
    DB_PATH.unlink(missing_ok=True)
    with TestClient(app) as client:
        for server in lab.servers.values():
            assert all(sock.getsockname()[0] == "127.0.0.1" for sock in server.sockets)
            assert all(sock.getsockname()[1] in PERMITTED_PORTS for sock in server.sockets)
        first = client.post("/api/observations/run")
        assert first.status_code == 200
        assert all(row["state"] == "reachable" for row in first.json()["observations"])

        valid_token = lab.tokens["portal"]
        lab.tokens["portal"] = "deliberately-wrong-token"
        inconclusive = client.post("/api/observations/run").json()
        portal_result = next(row for row in inconclusive["observations"] if row["port"] == lab.ports["portal"])
        assert portal_result["state"] == "inconclusive"
        assert client.get("/api/incidents").json() == []
        lab.tokens["portal"] = valid_token

        started = client.post("/api/lab/management/start")
        assert started.status_code == 200
        assert started.json()["host"] == "127.0.0.1"
        assert started.json()["approved"] is False

        second = client.post("/api/observations/run")
        assert second.status_code == 200
        investigations = client.get("/api/investigations").json()
        assert len(investigations) == 1
        case = investigations[0]
        assert case["asset"] == "ASTERGATE-BACKUP-01"
        assert case["port"] == started.json()["port"]
        assert case["rule_ids"] == ["R001", "R002", "R007"]
        assert case["previous_state"] == "unavailable"
        assert case["current_state"] == "reachable"
        assert case["approved"] is False
        assert case["source_mode"] == "local_lab_observation"
        assert "127.0.0.1" in case["evidence"]
        assert "does not establish internet exposure" in case["explanation"]

        premature_resolution = client.patch("/api/incidents/1", json={"status": "resolved"})
        assert premature_resolution.status_code == 409

        client.post("/api/observations/run")
        assert len(client.get("/api/investigations").json()) == 1
        stopped = client.post("/api/lab/management/stop")
        assert stopped.json()["status"] == "stopped"
        verified = client.post("/api/demo/remediate")
        assert verified.status_code == 200
        case = client.get("/api/incidents/1").json()
        assert case["status"] == "resolved"
        assert case["current_state"] == "unavailable"

        dns = client.post("/api/demo/scenarios/dns-drift/run").json()["result"]
        assert dns["changed"] is True
        assert "A" in dns["differences"]
        assert dns["source_mode"] == "synthetic_external_snapshot"
        dns_repeat = client.post("/api/demo/scenarios/dns-drift/run").json()["result"]
        assert dns_repeat["changed"] is True
        assert dns_repeat["case_id"] == dns["case_id"]

        tls = client.post("/api/demo/scenarios/tls-change/run").json()["result"]
        assert tls["changed"] is True
        assert "fingerprint" in tls["differences"]
        assert tls["source_mode"] == "synthetic_external_snapshot"

        before_approved = len(client.get("/api/incidents").json())
        approved = client.post("/api/demo/scenarios/approved-maintenance/run")
        assert approved.status_code == 200
        after_approved = client.get("/api/incidents").json()
        assert len(after_approved) == before_approved
        assert any(change["scenario_id"] == "approved-maintenance" for change in client.get("/api/changes").json())

        reset = client.post("/api/demo/reset")
        assert reset.status_code == 200
        assert reset.json()["active_scenario"] == "baseline"
        assert client.get("/api/incidents").json() == []
        assert len(client.get("/api/assets").json()) == 3


def test_observer_rejects_unregistered_port():
    with TestClient(app) as client:
        with SessionLocal() as db:
            asset = db.scalar(select(Asset).where(Asset.name == "ASTERGATE-APP-01"))
            rogue = LabService(asset_id=asset.id, name="unregistered", port=12345, approved=False, kind="rogue")
            db.add(rogue)
            db.commit()
        response = client.post("/api/observations/run")
        assert response.status_code == 400
        assert "registered loopback lab" in response.json()["detail"]
        with SessionLocal() as db:
            rogue = db.scalar(select(LabService).where(LabService.name == "unregistered"))
            db.delete(rogue)
            db.commit()


def test_port_conflict_uses_another_registered_port_without_touching_conflict():
    async def scenario():
        blocker = socket.socket()
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", PERMITTED_PORTS.start))
        blocker.listen()
        local_lab = LocalLab()
        try:
            chosen = await local_lab.start("conflict-test")
            assert chosen != PERMITTED_PORTS.start
            assert chosen in PERMITTED_PORTS
            assert blocker.getsockname()[1] == PERMITTED_PORTS.start
        finally:
            await local_lab.stop_all()
            blocker.close()
    asyncio.run(scenario())

