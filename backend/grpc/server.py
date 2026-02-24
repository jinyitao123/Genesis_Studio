from __future__ import annotations

import os

from .service import create_grpc_server


def serve_grpc() -> None:
    port = int(os.getenv("GRPC_PORT", "50051"))
    server = create_grpc_server()
    _ = server.add_insecure_port(f"[::]:{port}")
    _ = server.start()
    server.wait_for_termination()
