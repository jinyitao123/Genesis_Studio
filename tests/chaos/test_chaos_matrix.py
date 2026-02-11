from __future__ import annotations

from pathlib import Path


def test_chaos_gate_script_exists_and_has_restart_step():
    script_path = Path("perf/chaos_gate.sh")
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")
    assert "docker compose restart" in content
    assert "for svc in query-api command-api redis neo4j" in content


def test_chaos_gate_has_health_assertions():
    script_path = Path("perf/chaos_gate.sh")
    content = script_path.read_text(encoding="utf-8")
    assert "api/health" in content
    assert "assert" in content


def test_perf_chaos_workflow_includes_k6_gate():
    workflow_path = Path(".github/workflows/perf-chaos-gate.yml")
    assert workflow_path.exists()
    content = workflow_path.read_text(encoding="utf-8")
    assert "grafana/k6" in content
    assert "k6_smoke.js" in content
