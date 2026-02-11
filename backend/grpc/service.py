from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from typing import Any

import grpc


config_module = import_module("backend.config")
deps_module = import_module("backend.ontology.deps")
pb2_module = import_module("backend.grpc.generated.genesis_contract_pb2")
pb2_grpc_module = import_module("backend.grpc.generated.genesis_contract_pb2_grpc")

load_settings: Any = getattr(config_module, "load_settings")
create_repository: Any = getattr(deps_module, "create_repository")
genesis_contract_pb2: Any = pb2_module
genesis_contract_pb2_grpc: Any = pb2_grpc_module


class CommandProjectionService(genesis_contract_pb2_grpc.CommandProjectionServiceServicer):
    @staticmethod
    def _set_operation_metadata(context, operation: str, status: str) -> None:
        context.set_trailing_metadata(
            (
                ("x-genesis-service", "command-projection"),
                ("x-genesis-operation", operation),
                ("x-genesis-status", status),
            )
        )

    def Health(self, request, context):
        _ = request
        self._set_operation_metadata(context, "Health", "ok")
        health_reply = getattr(genesis_contract_pb2, "HealthReply")
        return health_reply(status="ok", service="grpc-command-projection")

    def CreateProjection(self, request, context):
        settings = load_settings()
        repo = create_repository(settings)
        try:
            projection_reply = getattr(genesis_contract_pb2, "ProjectionReply")
            snapshot = repo.create_projection_snapshot()
            repo.append_audit_log(request.actor or "grpc", "create_projection_grpc", snapshot.projection_id)
            self._set_operation_metadata(context, "CreateProjection", "ok")
            return projection_reply(
                projection_id=snapshot.projection_id,
                object_type_count=snapshot.object_type_count,
                event_count=snapshot.event_count,
            )
        except Exception as exc:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"grpc projection failed: {exc}")
            self._set_operation_metadata(context, "CreateProjection", "error")
            projection_reply = getattr(genesis_contract_pb2, "ProjectionReply")
            return projection_reply()
        finally:
            repo.close()


def create_grpc_server(max_workers: int = 10) -> grpc.Server:
    server = grpc.server(ThreadPoolExecutor(max_workers=max_workers))
    genesis_contract_pb2_grpc.add_CommandProjectionServiceServicer_to_server(CommandProjectionService(), server)
    return server
