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
