from __future__ import annotations

import os
from importlib import import_module
from typing import Any

import grpc


pb2_module = import_module("backend.grpc.generated.genesis_contract_pb2")
pb2_grpc_module = import_module("backend.grpc.generated.genesis_contract_pb2_grpc")
genesis_contract_pb2: Any = pb2_module
genesis_contract_pb2_grpc: Any = pb2_grpc_module


def _grpc_target(explicit_target: str | None = None) -> str:
    if explicit_target:
        return explicit_target
    return os.getenv("GRPC_TARGET", "localhost:50051")


def call_health(target: str | None = None) -> tuple[str, str]:
    resolved_target = _grpc_target(target)
    with grpc.insecure_channel(resolved_target) as channel:
        stub = genesis_contract_pb2_grpc.CommandProjectionServiceStub(channel)
        health_request = getattr(genesis_contract_pb2, "HealthRequest")
        response = stub.Health(health_request())
        return response.status, response.service


def call_create_projection(actor: str, target: str | None = None) -> str:
    resolved_target = _grpc_target(target)
    with grpc.insecure_channel(resolved_target) as channel:
        stub = genesis_contract_pb2_grpc.CommandProjectionServiceStub(channel)
        projection_request = getattr(genesis_contract_pb2, "ProjectionRequest")
        response = stub.CreateProjection(projection_request(actor=actor))
        return response.projection_id
