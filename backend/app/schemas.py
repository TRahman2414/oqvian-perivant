from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CaseStatus = Literal["new", "acknowledged", "investigating", "approved_change", "remediation_planned", "resolved", "reopened"]


class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: CaseStatus | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("owner")
    @classmethod
    def strip_owner(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Owner cannot be blank")
        return value.strip() if value else value

    @model_validator(mode="after")
    def require_change(self):
        if self.status is None and self.owner is None:
            raise ValueError("Provide a status or owner update")
        return self


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=2000)
    author: str = Field(default="Demo Analyst", min_length=1, max_length=120)

    @field_validator("content", "author")
    @classmethod
    def strip_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be blank")
        return value.strip()


class SnapshotCompare(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["dns", "tls"]
