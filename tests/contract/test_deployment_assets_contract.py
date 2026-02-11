from __future__ import annotations

from pathlib import Path


def test_k8s_assets_cover_core_services():
    required = {
        "k8s/namespace.yaml",
        "k8s/gateway.yaml",
        "k8s/query-api.yaml",
        "k8s/command-api.yaml",
        "k8s/worker.yaml",
        "k8s/grpc-api.yaml",
        "k8s/neo4j.yaml",
        "k8s/redis.yaml",
        "k8s/postgres.yaml",
    }
    for item in required:
        assert Path(item).exists(), item


def test_helm_templates_cover_core_services():
    required = {
        "helm/genesis-studio/templates/query-api-deployment.yaml",
        "helm/genesis-studio/templates/command-api-deployment.yaml",
        "helm/genesis-studio/templates/gateway-deployment.yaml",
        "helm/genesis-studio/templates/worker-deployment.yaml",
        "helm/genesis-studio/templates/grpc-api-deployment.yaml",
        "helm/genesis-studio/templates/neo4j-deployment.yaml",
        "helm/genesis-studio/templates/redis-deployment.yaml",
        "helm/genesis-studio/templates/postgres-deployment.yaml",
    }
    for item in required:
        assert Path(item).exists(), item


def test_argocd_and_dr_drill_assets_exist():
    assert Path("argocd/application.yaml").exists()
    assert Path("dr/dr_plan.md").exists()
    assert Path("dr/drill_scripts/run_drill.sh").exists()


def test_workflows_cover_dr_and_e2e_pact():
    dr_workflow = Path(".github/workflows/dr-drill.yml").read_text(encoding="utf-8")
    assert "drill" in dr_workflow
    assert "run_drill.sh" in dr_workflow

    e2e_workflow = Path(".github/workflows/e2e-pact.yml").read_text(encoding="utf-8")
    assert "tests/e2e" in e2e_workflow
    assert "tests/pact" in e2e_workflow


def test_workflows_cover_runbook_and_perf_multi_scenario():
    runbook_workflow = Path(".github/workflows/runbook-automation.yml").read_text(encoding="utf-8")
    assert "ops/runbooks/recover_query_api.sh" in runbook_workflow
    assert "ops/runbooks/recover_redis_backlog.sh" in runbook_workflow

    perf_workflow = Path(".github/workflows/perf-multi-scenario.yml").read_text(encoding="utf-8")
    assert "k6_projection_replay.js" in perf_workflow
    assert "k6_lineage_query.js" in perf_workflow
