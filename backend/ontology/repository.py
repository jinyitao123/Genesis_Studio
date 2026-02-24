from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from typing import Any
from uuid import uuid4

from neo4j import Driver
from neo4j import GraphDatabase

from .schemas import ActionDispatch
from .schemas import ActionEvent
from .schemas import DispatchTransactionRecord
from .schemas import LogicGateResult
from .schemas import ObjectTypeCreate
from .schemas import ObjectTypeDTO
from .schemas import ProjectionSnapshot
from .schemas import TransactionLineage


class Neo4jOntologyRepository:
    def __init__(self, uri: str, user: str, password: str):
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def ping(self) -> bool:
        with self._driver.session() as session:
            record = session.run("RETURN 1 AS ok").single()
            return bool(record and record.get("ok") == 1)

    def create_object_type(self, payload: ObjectTypeCreate) -> ObjectTypeDTO:
        now = datetime.now(timezone.utc)
        with self._driver.session() as session:
            record = session.run(
                """
                MERGE (t:ObjectType {type_uri: $type_uri})
                SET t.display_name = $display_name,
                    t.parent_type = $parent_type,
                    t.tags = $tags,
                    t.created_at = $created_at
                RETURN t.type_uri AS type_uri,
                       t.display_name AS display_name,
                       t.parent_type AS parent_type,
                       t.tags AS tags,
                       t.created_at AS created_at
                """,
                type_uri=payload.type_uri,
                display_name=payload.display_name,
                parent_type=payload.parent_type,
                tags=payload.tags,
                created_at=now.isoformat(),
            ).single()

        if record is None:
            raise RuntimeError("failed to create object type")

        return ObjectTypeDTO(
            type_uri=record["type_uri"],
            display_name=record["display_name"],
            parent_type=record["parent_type"],
            tags=list(record["tags"] or []),
            created_at=datetime.fromisoformat(record["created_at"]),
        )

    def append_audit_log(self, actor: str, operation: str, detail: str) -> None:
        now = datetime.now(timezone.utc)
        with self._driver.session() as session:
            _ = session.run(
                """
                CREATE (a:AuditLog {
                    audit_id: $audit_id,
                    actor: $actor,
                    operation: $operation,
                    detail: $detail,
                    created_at: $created_at
                })
                """,
                audit_id=str(uuid4()),
                actor=actor,
                operation=operation,
                detail=detail,
                created_at=now.isoformat(),
            )

    def list_object_types(self) -> list[ObjectTypeDTO]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (t:ObjectType)
                RETURN t.type_uri AS type_uri,
                       t.display_name AS display_name,
                       t.parent_type AS parent_type,
                       t.tags AS tags,
                       t.created_at AS created_at
                ORDER BY t.type_uri
                """
            )
            results = []
            for row in rows:
                created = row["created_at"]
                created_at = datetime.fromisoformat(created) if created else datetime.now(timezone.utc)
                results.append(
                    ObjectTypeDTO(
                        type_uri=row["type_uri"],
                        display_name=row["display_name"],
                        parent_type=row["parent_type"],
                        tags=list(row["tags"] or []),
                        created_at=created_at,
                    )
                )

        return results

    def dispatch_action(self, payload: ActionDispatch) -> ActionEvent:
        event_id = str(uuid4())
        now = datetime.now(timezone.utc)
        serialized_payload = json.dumps(payload.payload)

        with self._driver.session() as session:
            record = session.run(
                """
                CREATE (e:DomainEvent {
                    event_id: $event_id,
                    action_id: $action_id,
                    source_id: $source_id,
                    target_id: $target_id,
                    payload_json: $payload_json,
                    created_at: $created_at
                })
                RETURN e.event_id AS event_id,
                       e.action_id AS action_id,
                       e.source_id AS source_id,
                       e.target_id AS target_id,
                       e.payload_json AS payload_json,
                       e.created_at AS created_at
                """,
                event_id=event_id,
                action_id=payload.action_id,
                source_id=payload.source_id,
                target_id=payload.target_id,
                payload_json=serialized_payload,
                created_at=now.isoformat(),
            ).single()

        if record is None:
            raise RuntimeError("failed to dispatch action")

        return ActionEvent(
            event_id=record["event_id"],
            action_id=record["action_id"],
            source_id=record["source_id"],
            target_id=record["target_id"],
            payload=json.loads(record["payload_json"]),
            created_at=datetime.fromisoformat(record["created_at"]),
        )

    def create_dispatch_transaction(
        self,
        *,
        txn_id: str,
        action_id: str,
        actor: str,
        status: str,
        event_id: str | None,
        compensation_event_id: str | None,
        gates: list[LogicGateResult],
    ) -> DispatchTransactionRecord:
        now = datetime.now(timezone.utc)
        serialized_gates = json.dumps([gate.model_dump(mode="json") for gate in gates])

        with self._driver.session() as session:
            record = session.run(
                """
                CREATE (t:DispatchTransaction {
                    txn_id: $txn_id,
                    action_id: $action_id,
                    actor: $actor,
                    status: $status,
                    event_id: $event_id,
                    compensation_event_id: $compensation_event_id,
                    gates_json: $gates_json,
                    created_at: $created_at,
                    reverted_at: NULL
                })
                RETURN t.txn_id AS txn_id,
                       t.action_id AS action_id,
                       t.actor AS actor,
                       t.status AS status,
                       t.event_id AS event_id,
                       t.compensation_event_id AS compensation_event_id,
                       t.gates_json AS gates_json,
                       t.created_at AS created_at,
                       t.reverted_at AS reverted_at
                """,
                txn_id=txn_id,
                action_id=action_id,
                actor=actor,
                status=status,
                event_id=event_id,
                compensation_event_id=compensation_event_id,
                gates_json=serialized_gates,
                created_at=now.isoformat(),
            ).single()

        if record is None:
            raise RuntimeError("failed to create dispatch transaction")

        return self._to_dispatch_transaction_record(record)

    def list_dispatch_transactions(self, limit: int = 100) -> list[DispatchTransactionRecord]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (t:DispatchTransaction)
                RETURN t.txn_id AS txn_id,
                       t.action_id AS action_id,
                       t.actor AS actor,
                       t.status AS status,
                       t.event_id AS event_id,
                       t.compensation_event_id AS compensation_event_id,
                       t.gates_json AS gates_json,
                       t.created_at AS created_at,
                       t.reverted_at AS reverted_at
                ORDER BY t.created_at DESC
                LIMIT $limit
                """,
                limit=limit,
            )
            return [self._to_dispatch_transaction_record(row) for row in rows]

    def get_dispatch_transaction(self, txn_id: str) -> DispatchTransactionRecord | None:
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (t:DispatchTransaction {txn_id: $txn_id})
                RETURN t.txn_id AS txn_id,
                       t.action_id AS action_id,
                       t.actor AS actor,
                       t.status AS status,
                       t.event_id AS event_id,
                       t.compensation_event_id AS compensation_event_id,
                       t.gates_json AS gates_json,
                       t.created_at AS created_at,
                       t.reverted_at AS reverted_at
                LIMIT 1
                """,
                txn_id=txn_id,
            ).single()

        if record is None:
            return None
        return self._to_dispatch_transaction_record(record)

    def mark_dispatch_transaction_reverted(self, txn_id: str, compensation_event_id: str) -> DispatchTransactionRecord:
        now = datetime.now(timezone.utc)
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (t:DispatchTransaction {txn_id: $txn_id})
                SET t.status = 'reverted',
                    t.compensation_event_id = $compensation_event_id,
                    t.reverted_at = $reverted_at
                RETURN t.txn_id AS txn_id,
                       t.action_id AS action_id,
                       t.actor AS actor,
                       t.status AS status,
                       t.event_id AS event_id,
                       t.compensation_event_id AS compensation_event_id,
                       t.gates_json AS gates_json,
                       t.created_at AS created_at,
                       t.reverted_at AS reverted_at
                """,
                txn_id=txn_id,
                compensation_event_id=compensation_event_id,
                reverted_at=now.isoformat(),
            ).single()

        if record is None:
            raise RuntimeError("transaction not found")
        return self._to_dispatch_transaction_record(record)

    def get_transaction_lineage(self, txn_id: str) -> TransactionLineage | None:
        transaction = self.get_dispatch_transaction(txn_id)
        if transaction is None:
            return None

        primary_event = self.get_event_by_id(transaction.event_id) if transaction.event_id else None
        compensation_event = (
            self.get_event_by_id(transaction.compensation_event_id)
            if transaction.compensation_event_id
            else None
        )
        return TransactionLineage(
            transaction=transaction,
            primary_event=primary_event,
            compensation_event=compensation_event,
        )

    def create_projection_snapshot(self) -> ProjectionSnapshot:
        now = datetime.now(timezone.utc)
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (t:ObjectType)
                WITH count(t) AS object_type_count
                MATCH (e:DomainEvent)
                WITH object_type_count, count(e) AS event_count
                CREATE (p:ProjectionSnapshot {
                    projection_id: $projection_id,
                    object_type_count: object_type_count,
                    event_count: event_count,
                    created_at: $created_at
                })
                RETURN p.projection_id AS projection_id,
                       p.object_type_count AS object_type_count,
                       p.event_count AS event_count,
                       p.created_at AS created_at
                """,
                projection_id=str(uuid4()),
                created_at=now.isoformat(),
            ).single()

        if record is None:
            raise RuntimeError("failed to create projection snapshot")

        return ProjectionSnapshot(
            projection_id=record["projection_id"],
            object_type_count=int(record["object_type_count"]),
            event_count=int(record["event_count"]),
            created_at=datetime.fromisoformat(record["created_at"]),
        )

    def latest_projection_snapshot(self) -> ProjectionSnapshot | None:
        with self._driver.session() as session:
            record = session.run(
                """
                MATCH (p:ProjectionSnapshot)
                RETURN p.projection_id AS projection_id,
                       p.object_type_count AS object_type_count,
                       p.event_count AS event_count,
                       p.created_at AS created_at
                ORDER BY p.created_at DESC
                LIMIT 1
                """
            ).single()

        if record is None:
            return None

        return ProjectionSnapshot(
            projection_id=record["projection_id"],
            object_type_count=int(record["object_type_count"]),
            event_count=int(record["event_count"]),
            created_at=datetime.fromisoformat(record["created_at"]),
        )

    def list_events(self) -> list[ActionEvent]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (e:DomainEvent)
                RETURN e.event_id AS event_id,
                       e.action_id AS action_id,
                       e.source_id AS source_id,
                       e.target_id AS target_id,
                       e.payload_json AS payload_json,
                       e.created_at AS created_at
                ORDER BY e.created_at DESC
                """
            )
            return [self._to_action_event(row) for row in rows]

    def get_event_by_id(self, event_id: str) -> ActionEvent | None:
        with self._driver.session() as session:
            row = session.run(
                """
                MATCH (e:DomainEvent {event_id: $event_id})
                RETURN e.event_id AS event_id,
                       e.action_id AS action_id,
                       e.source_id AS source_id,
                       e.target_id AS target_id,
                       e.payload_json AS payload_json,
                       e.created_at AS created_at
                LIMIT 1
                """,
                event_id=event_id,
            ).single()

        if row is None:
            return None
        return self._to_action_event(row)

    def seed_demo_object_types(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._driver.session() as session:
            _ = session.run(
                """
                MERGE (a:ObjectType {type_uri: 'com.genesis.unit.Drone'})
                SET a.display_name = coalesce(a.display_name, 'Drone'),
                    a.parent_type = coalesce(a.parent_type, 'com.genesis.unit.AirUnit'),
                    a.tags = coalesce(a.tags, ['air', 'light']),
                    a.created_at = coalesce(a.created_at, $created_at)
                MERGE (b:ObjectType {type_uri: 'com.genesis.unit.Tank'})
                SET b.display_name = coalesce(b.display_name, 'Tank'),
                    b.parent_type = coalesce(b.parent_type, 'com.genesis.unit.GroundUnit'),
                    b.tags = coalesce(b.tags, ['ground', 'heavy']),
                    b.created_at = coalesce(b.created_at, $created_at)
                """,
                created_at=now,
            )

    def seed_demo_proposals(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._driver.session() as session:
            _ = session.run(
                """
                MERGE (p:Proposal {proposal_id: 'prop-ontology-opt-1'})
                SET p.title = coalesce(p.title, 'Optimize ontology migration gates'),
                    p.intent = coalesce(p.intent, 'Improve schema migration safety checks'),
                    p.status = coalesce(p.status, 'draft'),
                    p.created_at = coalesce(p.created_at, $created_at),
                    p.updated_at = coalesce(p.updated_at, $created_at)
                MERGE (q:Proposal {proposal_id: 'prop-routing-hardening-1'})
                SET q.title = coalesce(q.title, 'Harden event routing lineage'),
                    q.intent = coalesce(q.intent, 'Strengthen correlation and replay controls'),
                    q.status = coalesce(q.status, 'draft'),
                    q.created_at = coalesce(q.created_at, $created_at),
                    q.updated_at = coalesce(q.updated_at, $created_at)
                """,
                created_at=now,
            )

    def list_proposals(self) -> list[dict[str, str]]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (p:Proposal)
                RETURN p.proposal_id AS proposal_id,
                       p.title AS title,
                       p.intent AS intent,
                       p.status AS status,
                       p.created_at AS created_at,
                       p.updated_at AS updated_at
                ORDER BY p.proposal_id
                """
            )
            return [
                {
                    "proposal_id": str(row["proposal_id"]),
                    "title": str(row["title"]),
                    "intent": str(row["intent"]),
                    "status": str(row["status"]),
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]),
                }
                for row in rows
            ]

    def set_proposal_status(self, proposal_id: str, status: str) -> dict[str, str] | None:
        now = datetime.now(timezone.utc).isoformat()
        with self._driver.session() as session:
            row = session.run(
                """
                MATCH (p:Proposal {proposal_id: $proposal_id})
                SET p.status = $status,
                    p.updated_at = $updated_at
                RETURN p.proposal_id AS proposal_id,
                       p.title AS title,
                       p.intent AS intent,
                       p.status AS status,
                       p.created_at AS created_at,
                       p.updated_at AS updated_at
                LIMIT 1
                """,
                proposal_id=proposal_id,
                status=status,
                updated_at=now,
            ).single()

        if row is None:
            return None

        return {
            "proposal_id": str(row["proposal_id"]),
            "title": str(row["title"]),
            "intent": str(row["intent"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def create_compliance_record(self, action: str, subject_id: str, actor: str) -> dict[str, str]:
        now = datetime.now(timezone.utc).isoformat()
        record_id = str(uuid4())
        with self._driver.session() as session:
            row = session.run(
                """
                CREATE (c:ComplianceRecord {
                    record_id: $record_id,
                    action: $action,
                    subject_id: $subject_id,
                    actor: $actor,
                    recorded_at: $recorded_at
                })
                RETURN c.action AS action,
                       c.subject_id AS subject_id,
                       c.actor AS actor,
                       c.recorded_at AS recorded_at
                """,
                record_id=record_id,
                action=action,
                subject_id=subject_id,
                actor=actor,
                recorded_at=now,
            ).single()

        if row is None:
            raise RuntimeError("failed to create compliance record")

        return {
            "action": str(row["action"]),
            "subject_id": str(row["subject_id"]),
            "actor": str(row["actor"]),
            "recorded_at": str(row["recorded_at"]),
        }

    def list_compliance_records(self, limit: int = 200) -> list[dict[str, str]]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (c:ComplianceRecord)
                RETURN c.action AS action,
                       c.subject_id AS subject_id,
                       c.actor AS actor,
                       c.recorded_at AS recorded_at
                ORDER BY c.recorded_at DESC
                LIMIT $limit
                """,
                limit=limit,
            )
            return [
                {
                    "action": str(row["action"]),
                    "subject_id": str(row["subject_id"]),
                    "actor": str(row["actor"]),
                    "recorded_at": str(row["recorded_at"]),
                }
                for row in rows
            ]

    def seed_demo_graph(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._driver.session() as session:
            _ = session.run(
                """
                MERGE (a:GraphNode {node_id: 'unit.drone'})
                SET a.label = coalesce(a.label, '无人机'),
                    a.updated_at = coalesce(a.updated_at, $updated_at),
                    a.created_at = coalesce(a.created_at, $updated_at)
                MERGE (b:GraphNode {node_id: 'unit.tank'})
                SET b.label = coalesce(b.label, '坦克'),
                    b.updated_at = coalesce(b.updated_at, $updated_at),
                    b.created_at = coalesce(b.created_at, $updated_at)
                MERGE (c:GraphNode {node_id: 'unit.command'})
                SET c.label = coalesce(c.label, '指挥车'),
                    c.updated_at = coalesce(c.updated_at, $updated_at),
                    c.created_at = coalesce(c.created_at, $updated_at)
                MERGE (a)-[r1:GRAPH_LINK {label: '侦查'}]->(b)
                SET r1.updated_at = coalesce(r1.updated_at, $updated_at)
                MERGE (c)-[r2:GRAPH_LINK {label: '指挥'}]->(a)
                SET r2.updated_at = coalesce(r2.updated_at, $updated_at)
                """,
                updated_at=now,
            )

    def upsert_graph_node(self, node_id: str, label: str, actor: str) -> dict[str, str]:
        now = datetime.now(timezone.utc).isoformat()
        with self._driver.session() as session:
            row = session.run(
                """
                MERGE (n:GraphNode {node_id: $node_id})
                SET n.label = $label,
                    n.updated_by = $actor,
                    n.updated_at = $updated_at,
                    n.created_at = coalesce(n.created_at, $updated_at)
                RETURN n.node_id AS node_id,
                       n.label AS label
                """,
                node_id=node_id,
                label=label,
                actor=actor,
                updated_at=now,
            ).single()

        if row is None:
            raise RuntimeError("failed to upsert graph node")
        return {
            "node_id": str(row["node_id"]),
            "label": str(row["label"]),
        }

    def delete_graph_node(self, node_id: str) -> bool:
        with self._driver.session() as session:
            row = session.run(
                """
                MATCH (n:GraphNode {node_id: $node_id})
                WITH n, count(n) AS cnt
                DETACH DELETE n
                RETURN cnt AS deleted
                """,
                node_id=node_id,
            ).single()

        if row is None:
            return False
        return int(row["deleted"] or 0) > 0

    def upsert_graph_edge(self, source_id: str, target_id: str, label: str, actor: str) -> dict[str, str]:
        now = datetime.now(timezone.utc).isoformat()
        with self._driver.session() as session:
            row = session.run(
                """
                MERGE (s:GraphNode {node_id: $source_id})
                ON CREATE SET s.label = $source_id, s.created_at = $updated_at
                SET s.updated_at = $updated_at
                MERGE (t:GraphNode {node_id: $target_id})
                ON CREATE SET t.label = $target_id, t.created_at = $updated_at
                SET t.updated_at = $updated_at
                MERGE (s)-[r:GRAPH_LINK {label: $label}]->(t)
                SET r.updated_at = $updated_at,
                    r.updated_by = $actor
                RETURN s.node_id AS source_id,
                       t.node_id AS target_id,
                       r.label AS label
                """,
                source_id=source_id,
                target_id=target_id,
                label=label,
                actor=actor,
                updated_at=now,
            ).single()

        if row is None:
            raise RuntimeError("failed to upsert graph edge")
        return {
            "source_id": str(row["source_id"]),
            "target_id": str(row["target_id"]),
            "label": str(row["label"]),
        }

    def delete_graph_edge(self, source_id: str, target_id: str, label: str) -> bool:
        with self._driver.session() as session:
            row = session.run(
                """
                MATCH (:GraphNode {node_id: $source_id})-[r:GRAPH_LINK {label: $label}]->(:GraphNode {node_id: $target_id})
                WITH r, count(r) AS cnt
                DELETE r
                RETURN cnt AS deleted
                """,
                source_id=source_id,
                target_id=target_id,
                label=label,
            ).single()

        if row is None:
            return False
        return int(row["deleted"] or 0) > 0

    def list_graph_nodes(self) -> list[dict[str, str]]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (n:GraphNode)
                RETURN n.node_id AS node_id,
                       n.label AS label
                ORDER BY n.node_id
                """
            )
            return [
                {
                    "node_id": str(row["node_id"]),
                    "label": str(row["label"]),
                }
                for row in rows
            ]

    def list_graph_edges(self) -> list[dict[str, str]]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (s:GraphNode)-[r:GRAPH_LINK]->(t:GraphNode)
                RETURN s.node_id AS source_id,
                       t.node_id AS target_id,
                       r.label AS label
                ORDER BY s.node_id, t.node_id, r.label
                """
            )
            return [
                {
                    "edge_id": f"{row['source_id']}:{row['target_id']}:{row['label']}",
                    "source_id": str(row["source_id"]),
                    "target_id": str(row["target_id"]),
                    "label": str(row["label"]),
                }
                for row in rows
            ]

    @staticmethod
    def _to_action_event(row: Any) -> ActionEvent:
        return ActionEvent(
            event_id=row["event_id"],
            action_id=row["action_id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            payload=json.loads(row["payload_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _to_dispatch_transaction_record(row: Any) -> DispatchTransactionRecord:
        gates_raw = json.loads(row["gates_json"]) if row["gates_json"] else []
        gates = [LogicGateResult(**gate) for gate in gates_raw]

        created_at = datetime.fromisoformat(row["created_at"])
        reverted_at_raw = row["reverted_at"]
        reverted_at = datetime.fromisoformat(reverted_at_raw) if reverted_at_raw else None

        return DispatchTransactionRecord(
            txn_id=row["txn_id"],
            action_id=row["action_id"],
            actor=row["actor"],
            status=row["status"],
            event_id=row["event_id"],
            compensation_event_id=row["compensation_event_id"],
            gates=gates,
            created_at=created_at,
            reverted_at=reverted_at,
        )
