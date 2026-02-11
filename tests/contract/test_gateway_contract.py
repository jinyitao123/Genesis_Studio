from __future__ import annotations

from pathlib import Path


def test_gateway_compose_service_exists():
    compose_path = Path("docker-compose.yml")
    content = compose_path.read_text(encoding="utf-8")
    assert "gateway:" in content
    assert "genesis-gateway" in content
    assert "18080:8080" in content


def test_gateway_nginx_routes_cover_query_and_command():
    nginx_path = Path("gateway/nginx.conf")
    content = nginx_path.read_text(encoding="utf-8")
    assert "resolver 127.0.0.11" in content
    assert "location /api/query/" in content
    assert "proxy_pass http://$query_upstream:5000;" in content
    assert "location /api/command/" in content
    assert "proxy_pass http://$command_upstream:8000;" in content
    assert "location /api/auth/" in content
    assert "location /api/compliance/" in content
    assert "location /ws/" in content
    assert "proxy_pass http://$frontend_upstream:5173;" in content
