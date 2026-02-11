from __future__ import annotations

import subprocess


def docker_status() -> dict[str, str | bool]:
    try:
        import docker
    except ModuleNotFoundError:
        return {
            "available": False,
            "method": "python-sdk",
            "reason": "docker package not installed",
        }

    try:
        client = docker.from_env()
        _ = client.ping()
        return {"available": True, "method": "python-sdk", "reason": "ok"}
    except Exception as sdk_error:
        try:
            _ = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            )
            return {"available": True, "method": "docker-cli", "reason": "ok"}
        except Exception as cli_error:
            return {
                "available": False,
                "method": "docker-cli",
                "reason": f"sdk_error={sdk_error}; cli_error={cli_error}",
            }
