from __future__ import annotations

import csv
import io
from uuid import uuid4

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import UploadFile

from .models import AddPropertyRequest
from .models import CreateClassRequest
from .models import CreateEntityRequest
from .models import CreateLinkRequest
from .models import CreateRelationRequest
from .models import OFClass
from .models import OFEntity
from .models import OFLink
from .models import OFProperty
from .models import OFRelation
from .models import PatchLinkLabelRequest
from .storage import load_graph
from .storage import load_ontology
from .storage import save_graph
from .storage import save_ontology

ontoflow_command_router = APIRouter(prefix="/api/ontoflow", tags=["ontoflow"])


# ──────────────────────────────────────────────────────────────────────────────
# Classes
# ──────────────────────────────────────────────────────────────────────────────

@ontoflow_command_router.post("/classes")
def create_class(body: CreateClassRequest) -> dict[str, object]:
    ontology = load_ontology()
    if any(c.name == body.name for c in ontology.classes):
        raise HTTPException(status_code=409, detail="类名已存在")
    new_cls = OFClass(id=str(uuid4()), name=body.name, description=body.description)
    ontology.classes.append(new_cls)
    save_ontology(ontology)
    return new_cls.model_dump(mode="json")


@ontoflow_command_router.delete("/classes/{class_id}")
def delete_class(class_id: str) -> dict[str, object]:
    ontology = load_ontology()
    cls = next((c for c in ontology.classes if c.id == class_id), None)
    if cls is None:
        raise HTTPException(status_code=404, detail="类不存在")
    ontology.classes = [c for c in ontology.classes if c.id != class_id]
    # cascade: remove relations referencing this class
    ontology.relations = [
        r for r in ontology.relations
        if r.source_class_id != class_id and r.target_class_id != class_id
    ]
    save_ontology(ontology)
    # cascade: remove entities of this class and their links
    graph = load_graph()
    removed_ids = {e.id for e in graph.entities if e.class_id == class_id}
    graph.entities = [e for e in graph.entities if e.class_id != class_id]
    graph.links = [
        lnk for lnk in graph.links
        if lnk.source_entity_id not in removed_ids and lnk.target_entity_id not in removed_ids
    ]
    save_graph(graph)
    return {"deleted": True}


# ──────────────────────────────────────────────────────────────────────────────
# Properties
# ──────────────────────────────────────────────────────────────────────────────

@ontoflow_command_router.post("/classes/{class_id}/properties")
def add_property(class_id: str, body: AddPropertyRequest) -> dict[str, object]:
    ontology = load_ontology()
    cls = next((c for c in ontology.classes if c.id == class_id), None)
    if cls is None:
        raise HTTPException(status_code=404, detail="类不存在")
    if any(p.name == body.name for p in cls.properties):
        raise HTTPException(status_code=409, detail="属性名已存在")
    if body.type not in ("string", "number"):
        raise HTTPException(status_code=422, detail="属性类型必须为 string 或 number")
    new_prop = OFProperty(id=str(uuid4()), name=body.name, type=body.type, unique=body.unique)
    cls.properties.append(new_prop)
    save_ontology(ontology)
    return new_prop.model_dump(mode="json")


@ontoflow_command_router.delete("/classes/{class_id}/properties/{prop_id}")
def delete_property(class_id: str, prop_id: str) -> dict[str, object]:
    ontology = load_ontology()
    cls = next((c for c in ontology.classes if c.id == class_id), None)
    if cls is None:
        raise HTTPException(status_code=404, detail="类不存在")
    if not any(p.id == prop_id for p in cls.properties):
        raise HTTPException(status_code=404, detail="属性不存在")
    cls.properties = [p for p in cls.properties if p.id != prop_id]
    save_ontology(ontology)
    return {"deleted": True}


# ──────────────────────────────────────────────────────────────────────────────
# Relations
# ──────────────────────────────────────────────────────────────────────────────

@ontoflow_command_router.post("/relations")
def create_relation(body: CreateRelationRequest) -> dict[str, object]:
    ontology = load_ontology()
    if not any(c.id == body.source_class_id for c in ontology.classes):
        raise HTTPException(status_code=404, detail="源类不存在")
    if not any(c.id == body.target_class_id for c in ontology.classes):
        raise HTTPException(status_code=404, detail="目标类不存在")
    if any(r.name == body.name for r in ontology.relations):
        raise HTTPException(status_code=409, detail="关系名已存在")
    new_rel = OFRelation(
        id=str(uuid4()),
        name=body.name,
        source_class_id=body.source_class_id,
        target_class_id=body.target_class_id,
        description=body.description,
    )
    ontology.relations.append(new_rel)
    save_ontology(ontology)
    return new_rel.model_dump(mode="json")


@ontoflow_command_router.delete("/relations/{relation_id}")
def delete_relation(relation_id: str) -> dict[str, object]:
    ontology = load_ontology()
    if not any(r.id == relation_id for r in ontology.relations):
        raise HTTPException(status_code=404, detail="关系不存在")
    ontology.relations = [r for r in ontology.relations if r.id != relation_id]
    save_ontology(ontology)
    # cascade: remove links using this relation
    graph = load_graph()
    graph.links = [lnk for lnk in graph.links if lnk.relation_id != relation_id]
    save_graph(graph)
    return {"deleted": True}


# ──────────────────────────────────────────────────────────────────────────────
# Entities
# ──────────────────────────────────────────────────────────────────────────────

@ontoflow_command_router.post("/entities")
def create_entity(body: CreateEntityRequest) -> dict[str, object]:
    ontology = load_ontology()
    cls = next((c for c in ontology.classes if c.id == body.class_id), None)
    if cls is None:
        raise HTTPException(status_code=404, detail="类不存在")
    # Validate numeric props
    for prop in cls.properties:
        val = body.properties.get(prop.name)
        if prop.type == "number" and val is not None and val != "":
            try:
                float(str(val))
            except ValueError:
                raise HTTPException(status_code=422, detail=f"属性 {prop.name} 必须为数字")
    entity = OFEntity(id=str(uuid4()), class_id=body.class_id, properties=body.properties)
    graph = load_graph()
    graph.entities.append(entity)
    save_graph(graph)
    return entity.model_dump(mode="json")


@ontoflow_command_router.delete("/entities/{entity_id}")
def delete_entity(entity_id: str) -> dict[str, object]:
    graph = load_graph()
    if not any(e.id == entity_id for e in graph.entities):
        raise HTTPException(status_code=404, detail="实体不存在")
    graph.entities = [e for e in graph.entities if e.id != entity_id]
    graph.links = [
        lnk for lnk in graph.links
        if lnk.source_entity_id != entity_id and lnk.target_entity_id != entity_id
    ]
    save_graph(graph)
    return {"deleted": True}


# ──────────────────────────────────────────────────────────────────────────────
# Links (entity ↔ entity)
# ──────────────────────────────────────────────────────────────────────────────

@ontoflow_command_router.post("/links")
def create_link(body: CreateLinkRequest) -> dict[str, object]:
    graph = load_graph()
    ontology = load_ontology()
    rel = next((r for r in ontology.relations if r.id == body.relation_id), None)
    if rel is None:
        raise HTTPException(status_code=404, detail="关系类型不存在")
    src = next((e for e in graph.entities if e.id == body.source_entity_id), None)
    tgt = next((e for e in graph.entities if e.id == body.target_entity_id), None)
    if src is None or tgt is None:
        raise HTTPException(status_code=404, detail="实体不存在")
    # Validate class compatibility
    if src.class_id != rel.source_class_id or tgt.class_id != rel.target_class_id:
        raise HTTPException(status_code=409, detail="关系类型不兼容")
    link = OFLink(
        id=str(uuid4()),
        source_entity_id=body.source_entity_id,
        target_entity_id=body.target_entity_id,
        relation_id=body.relation_id,
        label=rel.name,
    )
    graph.links.append(link)
    save_graph(graph)
    return link.model_dump(mode="json")


@ontoflow_command_router.patch("/links/{link_id}/label")
def patch_link_label(link_id: str, body: PatchLinkLabelRequest) -> dict[str, object]:
    graph = load_graph()
    link = next((lnk for lnk in graph.links if lnk.id == link_id), None)
    if link is None:
        raise HTTPException(status_code=404, detail="链接不存在")
    link.label = body.label
    save_graph(graph)
    return link.model_dump(mode="json")


@ontoflow_command_router.delete("/links/{link_id}")
def delete_link(link_id: str) -> dict[str, object]:
    graph = load_graph()
    if not any(lnk.id == link_id for lnk in graph.links):
        raise HTTPException(status_code=404, detail="链接不存在")
    graph.links = [lnk for lnk in graph.links if lnk.id != link_id]
    save_graph(graph)
    return {"deleted": True}


# ──────────────────────────────────────────────────────────────────────────────
# CSV import
# ──────────────────────────────────────────────────────────────────────────────

@ontoflow_command_router.post("/import/csv")
async def import_csv(file: UploadFile, class_id: str) -> dict[str, object]:
    ontology = load_ontology()
    cls = next((c for c in ontology.classes if c.id == class_id), None)
    if cls is None:
        raise HTTPException(status_code=404, detail="类不存在")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="无法导入：无匹配本体属性")

    prop_names = {p.name for p in cls.properties}
    matched = [col for col in reader.fieldnames if col in prop_names]
    if not matched:
        raise HTTPException(status_code=422, detail="无法导入：无匹配本体属性")

    graph = load_graph()
    count = 0
    for row in reader:
        props: dict[str, str | int | float | bool | None] = {}
        for name in matched:
            val: str | int | float | bool | None = row.get(name)
            # coerce number fields
            prop_def = next((p for p in cls.properties if p.name == name), None)
            if prop_def and prop_def.type == "number" and val is not None:
                try:
                    props[name] = float(val) if "." in str(val) else int(val)
                except ValueError:
                    props[name] = val
            else:
                props[name] = val
        entity = OFEntity(id=str(uuid4()), class_id=class_id, properties=props)
        graph.entities.append(entity)
        count += 1

    save_graph(graph)
    return {"imported": count, "matched_columns": matched}


# ──────────────────────────────────────────────────────────────────────────────
# Persistence
# ──────────────────────────────────────────────────────────────────────────────

@ontoflow_command_router.post("/save")
def save_all() -> dict[str, object]:
    """Explicit save — no-op if auto-save already happened; idempotent."""
    ontology = load_ontology()
    graph = load_graph()
    save_ontology(ontology)
    save_graph(graph)
    return {"saved": True}
