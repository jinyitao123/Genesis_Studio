from __future__ import annotations

import json
import os
from pathlib import Path

from .models import OFGraph
from .models import OFOntology


_DEFAULT_DIR = Path.home() / "ontoflow"


def _storage_dir() -> Path:
    path = Path(os.getenv("ONTOFLOW_DATA_DIR", str(_DEFAULT_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_ontology() -> OFOntology:
    path = _storage_dir() / "ontology.json"
    if not path.exists():
        return OFOntology()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return OFOntology.model_validate(data)
    except Exception:
        return OFOntology()


def save_ontology(ontology: OFOntology) -> None:
    path = _storage_dir() / "ontology.json"
    path.write_text(ontology.model_dump_json(indent=2), encoding="utf-8")


def load_graph() -> OFGraph:
    path = _storage_dir() / "graph.json"
    if not path.exists():
        return OFGraph()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return OFGraph.model_validate(data)
    except Exception:
        return OFGraph()


def save_graph(graph: OFGraph) -> None:
    path = _storage_dir() / "graph.json"
    path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
