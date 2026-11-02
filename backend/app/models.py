from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(80))
    criticality: Mapped[str] = mapped_column(String(30))
    owner: Mapped[str] = mapped_column(String(120))
    demo: Mapped[bool] = mapped_column(Boolean, default=True)
    services: Mapped[list["LabService"]] = relationship(back_populates="asset")


class LabService(Base):
    __tablename__ = "lab_services"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    name: Mapped[str] = mapped_column(String(120))
    port: Mapped[int] = mapped_column(Integer, unique=True)
    protocol: Mapped[str] = mapped_column(String(12), default="tcp")
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    kind: Mapped[str] = mapped_column(String(30), default="baseline")
    asset: Mapped[Asset] = relationship(back_populates="services")


class ObservationRun(Base):
    __tablename__ = "observation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    source_mode: Mapped[str] = mapped_column(String(50), default="local_lab_observation")
    observations: Mapped[list["Observation"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("observation_runs.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("lab_services.id"))
    host: Mapped[str] = mapped_column(String(64), default="127.0.0.1")
    port: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[str] = mapped_column(Text)
    run: Mapped[ObservationRun] = relationship(back_populates="observations")


class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(160), unique=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="new")
    priority: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str] = mapped_column(String(120), default="Unassigned")
    confidence: Mapped[str] = mapped_column(String(30), default="evidence-backed")
    explanation: Mapped[str] = mapped_column(Text)
    rule_ids: Mapped[list[str]] = mapped_column(JSON)
    previous_state: Mapped[str] = mapped_column(String(30))
    current_state: Mapped[str] = mapped_column(String(30))
    host: Mapped[str] = mapped_column(String(64))
    port: Mapped[int] = mapped_column(Integer)
    approved: Mapped[bool] = mapped_column(Boolean)
    source_mode: Mapped[str] = mapped_column(String(50))
    evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    snapshot_type: Mapped[str] = mapped_column(String(20))
    snapshot_key: Mapped[str] = mapped_column(String(160))
    source_mode: Mapped[str] = mapped_column(String(50))
    values: Mapped[dict] = mapped_column(JSON)
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    scenario_id: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ChangeRequest(Base):
    __tablename__ = "change_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    title: Mapped[str] = mapped_column(String(160))
    approval_status: Mapped[str] = mapped_column(String(30))
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    details: Mapped[str] = mapped_column(Text)
    scenario_id: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class InvestigationNote(Base):
    __tablename__ = "investigation_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    author: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(120), default="Demo Analyst")
    previous_state: Mapped[str] = mapped_column(Text, default="")
    new_state: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

