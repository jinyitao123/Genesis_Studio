from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone

from flask import Blueprint
from flask import Response
from flask import jsonify
from flask import request

from .export import export_entities_csv
from .export import export_jsonld
from .export import export_turtle
from .storage import load_graph
from .storage import load_ontology

ontoflow_query_bp = Blueprint("ontoflow_query", __name__, url_prefix="/api/ontoflow")


@ontoflow_query_bp.get("/ontology")
def get_ontology():
    return jsonify(load_ontology().model_dump(mode="json"))


@ontoflow_query_bp.get("/graph")
def get_graph():
    return jsonify(load_graph().model_dump(mode="json"))


@ontoflow_query_bp.get("/export/turtle")
def export_turtle_route():
    ontology = load_ontology()
    if not ontology.classes and not ontology.relations:
        return jsonify({"detail": "本体未定义，无法导出"}), 400
    ttl = export_turtle(ontology)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        ttl,
        mimetype="text/turtle",
        headers={"Content-Disposition": f'attachment; filename="ontology_{date_str}.ttl"'},
    )


@ontoflow_query_bp.get("/export/jsonld")
def export_jsonld_route():
    ontology = load_ontology()
    if not ontology.classes and not ontology.relations:
        return jsonify({"detail": "本体未定义，无法导出"}), 400
    payload = export_jsonld(ontology)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/ld+json",
        headers={"Content-Disposition": f'attachment; filename="ontology_{date_str}.jsonld"'},
    )


@ontoflow_query_bp.get("/export/csv")
def export_csv_route():
    ontology = load_ontology()
    graph = load_graph()
    csv_str = export_entities_csv(ontology, graph)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        csv_str,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="entities_{date_str}.csv"'},
    )


@ontoflow_query_bp.get("/import/csv/preview")
def csv_import_preview():
    """Return ontology property IDs so the frontend can build the match table."""
    ontology = load_ontology()
    class_id = request.args.get("class_id", "")
    target_class = next((c for c in ontology.classes if c.id == class_id), None)
    props = [{"name": p.name, "type": p.type} for p in target_class.properties] if target_class else []
    return jsonify({"properties": props})
