# Test Matrix

## Contract
- REST contract: `tests/contract/test_rest_contract.py`
- gRPC contract: `tests/contract/test_grpc_contract.py`

## Chaos
- Chaos gate script checks: `tests/chaos/test_chaos_matrix.py`
- Restart simulation script: `perf/chaos_gate.sh`
- CI execution: `.github/workflows/perf-chaos-gate.yml`
- Performance budget gate: `perf/k6_smoke.js` executed in `.github/workflows/perf-chaos-gate.yml`

## Security
- Guardrails and ABAC tests: `tests/security/test_guardrails_and_abac.py`
- Auth + ABAC route coverage: `tests/test_command_api.py`, `tests/test_query_api.py`
- CI security gates: `.github/workflows/security-gate.yml` (Trivy + ZAP baseline)

## Core Regression
- Health and metrics: `tests/test_health.py`
- Command/query baseline: `tests/test_command_api.py`, `tests/test_query_api.py`
