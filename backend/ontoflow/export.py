from __future__ import annotations

import csv
import io

from .models import OFGraph
from .models import OFOntology


def export_turtle(ontology: OFOntology) -> str:
    lines: list[str] = [
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix onto: <http://ontoflow.local/ontology#> .",
        "",
        "<http://ontoflow.local/ontology>",
        "    a owl:Ontology .",
        "",
    ]

    class_by_id = {c.id: c for c in ontology.classes}

    for cls in ontology.classes:
        lines.append(f"onto:{cls.name}")
        lines.append("    a owl:Class ;")
        if cls.description:
            escaped = cls.description.replace('"', '\\"')
            lines.append(f'    rdfs:comment "{escaped}" ;')
        lines.append(f'    rdfs:label "{cls.name}" .')
        lines.append("")

        for prop in cls.properties:
            xsd_type = "xsd:decimal" if prop.type == "number" else "xsd:string"
            lines.append(f"onto:{cls.name}_{prop.name}")
            lines.append("    a owl:DatatypeProperty ;")
            lines.append(f"    rdfs:domain onto:{cls.name} ;")
            lines.append(f"    rdfs:range {xsd_type} ;")
            lines.append(f'    rdfs:label "{prop.name}" .')
            lines.append("")

    for rel in ontology.relations:
        src = class_by_id.get(rel.source_class_id)
        tgt = class_by_id.get(rel.target_class_id)
        if not src or not tgt:
            continue
        lines.append(f"onto:{rel.name}")
        lines.append("    a owl:ObjectProperty ;")
        lines.append(f"    rdfs:domain onto:{src.name} ;")
        lines.append(f"    rdfs:range onto:{tgt.name} ;")
        if rel.description:
            escaped = rel.description.replace('"', '\\"')
            lines.append(f'    rdfs:comment "{escaped}" ;')
        lines.append(f'    rdfs:label "{rel.name}" .')
        lines.append("")

    return "\n".join(lines)


def export_jsonld(ontology: OFOntology) -> dict[str, object]:
    base = "http://ontoflow.local/ontology#"
    graph: list[dict[str, object]] = []

    class_by_id = {c.id: c for c in ontology.classes}

    for cls in ontology.classes:
        node: dict[str, object] = {
            "@id": f"{base}{cls.name}",
            "@type": "owl:Class",
            "rdfs:label": cls.name,
        }
        if cls.description:
            node["rdfs:comment"] = cls.description
        graph.append(node)

        for prop in cls.properties:
            xsd_type = "xsd:decimal" if prop.type == "number" else "xsd:string"
            graph.append({
                "@id": f"{base}{cls.name}_{prop.name}",
                "@type": "owl:DatatypeProperty",
                "rdfs:domain": {"@id": f"{base}{cls.name}"},
                "rdfs:range": {"@id": xsd_type},
                "rdfs:label": prop.name,
            })

    for rel in ontology.relations:
        src = class_by_id.get(rel.source_class_id)
        tgt = class_by_id.get(rel.target_class_id)
        if not src or not tgt:
            continue
        rel_node: dict[str, object] = {
            "@id": f"{base}{rel.name}",
            "@type": "owl:ObjectProperty",
            "rdfs:domain": {"@id": f"{base}{src.name}"},
            "rdfs:range": {"@id": f"{base}{tgt.name}"},
            "rdfs:label": rel.name,
        }
        if rel.description:
            rel_node["rdfs:comment"] = rel.description
        graph.append(rel_node)

    return {
        "@context": {
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@graph": graph,
    }


def export_entities_csv(ontology: OFOntology, graph: OFGraph) -> str:
    class_by_id = {c.id: c for c in ontology.classes}
    buf = io.StringIO()

    # Collect all property names across all classes (as headers)
    all_prop_names: list[str] = []
    seen: set[str] = set()
    for cls in ontology.classes:
        for prop in cls.properties:
            if prop.name not in seen:
                all_prop_names.append(prop.name)
                seen.add(prop.name)

    writer = csv.DictWriter(buf, fieldnames=["id", "class"] + all_prop_names, lineterminator="\n")
    writer.writeheader()

    for entity in graph.entities:
        cls = class_by_id.get(entity.class_id)
        row: dict[str, object] = {
            "id": entity.id,
            "class": cls.name if cls else entity.class_id,
        }
        for name in all_prop_names:
            row[name] = entity.properties.get(name, "")
        writer.writerow(row)

    return buf.getvalue()
