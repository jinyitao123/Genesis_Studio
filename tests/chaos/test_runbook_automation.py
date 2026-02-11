from __future__ import annotations

from pathlib import Path


def test_runbook_scripts_exist_and_are_wired():
    query_script = Path("ops/runbooks/recover_query_api.sh")
    redis_script = Path("ops/runbooks/recover_redis_backlog.sh")
    assert query_script.exists()
    assert redis_script.exists()

    workflow = Path(".github/workflows/runbook-automation.yml").read_text(encoding="utf-8")
    assert "recover_query_api.sh" in workflow
    assert "recover_redis_backlog.sh" in workflow


def test_perf_multi_scenario_assets_exist():
    assert Path("perf/k6_projection_replay.js").exists()
    assert Path("perf/k6_lineage_query.js").exists()
    workflow = Path(".github/workflows/perf-multi-scenario.yml").read_text(encoding="utf-8")
    assert "k6_projection_replay.js" in workflow
    assert "k6_lineage_query.js" in workflow
