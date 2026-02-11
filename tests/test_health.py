from importlib import import_module


flask_app = import_module("backend.app").create_app()


def test_root_endpoint():
    client = flask_app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["name"] == "Genesis Studio"


def test_health_endpoint():
    client = flask_app.test_client()

    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "genesis-studio"


def test_dependency_health_endpoint():
    client = flask_app.test_client()

    response = client.get("/api/health/dependencies")
    assert response.status_code == 200
    payload = response.get_json()
    assert "docker" in payload
    assert "neo4j_uri" in payload


def test_metrics_endpoint():
    client = flask_app.test_client()

    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert b"genesis_http_requests_total" in response.data
