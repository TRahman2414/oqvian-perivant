from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import Asset, Snapshot
from app.main import normalize_snapshot


def test_dns_record_order_is_normalized():
    first = normalize_snapshot("dns", {"A": ["198.51.100.20", "192.0.2.10"], "MX": ["mail.example"]})
    reordered = normalize_snapshot("dns", {"MX": ["mail.example"], "A": ["192.0.2.10", "198.51.100.20"]})
    assert first == reordered


def test_identical_tls_snapshot_does_not_open_a_case():
    with TestClient(app) as client:
        assert client.post("/api/demo/reset").status_code == 200
        with SessionLocal() as db:
            asset = db.scalar(select(Asset).where(Asset.name == "ASTERGATE-PORTAL-01"))
            baseline = db.scalar(select(Snapshot).where(Snapshot.snapshot_type == "tls", Snapshot.scenario_id == "baseline"))
            db.add(Snapshot(asset_id=asset.id, snapshot_type="tls", snapshot_key=baseline.snapshot_key,
                            source_mode="synthetic_external_snapshot", values=baseline.values.copy(),
                            approved=True, scenario_id="identical-test"))
            db.commit()
        result = client.post("/api/snapshots/compare", json={"type": "tls"})
        assert result.status_code == 200
        assert result.json()["changed"] is False
        assert client.get("/api/incidents").json() == []
