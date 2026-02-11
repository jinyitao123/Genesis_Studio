from __future__ import annotations

from importlib import import_module

import grpc


def test_grpc_contract_health_and_projection(monkeypatch):
    grpc_service = import_module("backend.grpc.service")
    pb2 = import_module("backend.grpc.generated.genesis_contract_pb2")
    pb2_grpc = import_module("backend.grpc.generated.genesis_contract_pb2_grpc")

    class FakeSnapshot:
        projection_id = "proj-grpc-1"
        object_type_count = 3
        event_count = 7

    class FakeRepo:
        def create_projection_snapshot(self):
            return FakeSnapshot()

        def append_audit_log(self, actor, operation, detail):
            _ = (actor, operation, detail)

        def close(self):
            return None

    monkeypatch.setattr("backend.grpc.service.create_repository", lambda _settings: FakeRepo())

    server = grpc_service.create_grpc_server(max_workers=2)
    port = server.add_insecure_port("localhost:0")
    server.start()
    try:
        with grpc.insecure_channel(f"localhost:{port}") as channel:
            stub = pb2_grpc.CommandProjectionServiceStub(channel)
            health, health_call = stub.Health.with_call(pb2.HealthRequest())
            assert health.status == "ok"
            assert health.service == "grpc-command-projection"
            health_meta = dict(health_call.trailing_metadata() or [])
            assert health_meta.get("x-genesis-service") == "command-projection"
            assert health_meta.get("x-genesis-operation") == "Health"
            assert health_meta.get("x-genesis-status") == "ok"

            projection, projection_call = stub.CreateProjection.with_call(pb2.ProjectionRequest(actor="tester"))
            assert projection.projection_id == "proj-grpc-1"
            assert projection.object_type_count == 3
            assert projection.event_count == 7
            projection_meta = dict(projection_call.trailing_metadata() or [])
            assert projection_meta.get("x-genesis-service") == "command-projection"
            assert projection_meta.get("x-genesis-operation") == "CreateProjection"
            assert projection_meta.get("x-genesis-status") == "ok"
    finally:
        server.stop(0)
