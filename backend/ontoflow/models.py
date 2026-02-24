from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class OFProperty(BaseModel):
    id: str
    name: str
    type: str = "string"   # "string" | "number"
    unique: bool = False


class OFClass(BaseModel):
    id: str
    name: str
    description: str = ""
    properties: list[OFProperty] = Field(default_factory=list)


class OFRelation(BaseModel):
    id: str
    name: str
    source_class_id: str
    target_class_id: str
    description: str = ""


class OFOntology(BaseModel):
    classes: list[OFClass] = Field(default_factory=list)
    relations: list[OFRelation] = Field(default_factory=list)


class OFEntity(BaseModel):
    id: str
    class_id: str
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class OFLink(BaseModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    relation_id: str
    label: str


class OFGraph(BaseModel):
    entities: list[OFEntity] = Field(default_factory=list)
    links: list[OFLink] = Field(default_factory=list)


# ---- Request / Response models ----

class CreateClassRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


class AddPropertyRequest(BaseModel):
    name: str = Field(min_length=1)
    type: str = "string"
    unique: bool = False


class CreateRelationRequest(BaseModel):
    name: str = Field(min_length=1)
    source_class_id: str = Field(min_length=1)
    target_class_id: str = Field(min_length=1)
    description: str = ""


class CreateEntityRequest(BaseModel):
    class_id: str = Field(min_length=1)
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class CreateLinkRequest(BaseModel):
    source_entity_id: str = Field(min_length=1)
    target_entity_id: str = Field(min_length=1)
    relation_id: str = Field(min_length=1)


class PatchLinkLabelRequest(BaseModel):
    label: str = Field(min_length=1)
