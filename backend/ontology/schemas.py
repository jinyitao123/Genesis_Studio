from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class ObjectTypeCreate(BaseModel):
    type_uri: str = Field(min_length=3)
    display_name: str = Field(min_length=1)
    parent_type: str | None = None
    tags: list[str] = Field(default_factory=list)


class ObjectTypeDTO(ObjectTypeCreate):
    created_at: datetime


class ActionDispatch(BaseModel):
    action_id: str = Field(min_length=3)
    source_id: str | None = None
    target_id: str | None = None
    actor: str = "system"
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ActionEvent(BaseModel):
    event_id: str
    action_id: str
    source_id: str | None
    target_id: str | None
    payload: dict[str, str | int | float | bool | None]
    created_at: datetime


class LogicGateResult(BaseModel):
    tier: str
    passed: bool
    detail: str


class DispatchDryRunResponse(BaseModel):
    allowed: bool
    txn_preview_id: str
    gates: list[LogicGateResult]
    estimated_effects: list[str]


class DispatchTransactionRecord(BaseModel):
    txn_id: str
    action_id: str
    actor: str
    status: str
    event_id: str | None
    compensation_event_id: str | None = None
    gates: list[LogicGateResult]
    created_at: datetime
    reverted_at: datetime | None = None


class RevertTransactionResponse(BaseModel):
    txn_id: str
    status: str
    compensation_event_id: str | None


class TransactionLineage(BaseModel):
    transaction: DispatchTransactionRecord
    primary_event: ActionEvent | None
    compensation_event: ActionEvent | None


class ProjectionSnapshot(BaseModel):
    projection_id: str
    object_type_count: int
    event_count: int
    created_at: datetime
