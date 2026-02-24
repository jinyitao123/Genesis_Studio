# PRP v3.0 Remaining Work - Executable Batch Checklist

## Priority Order

1. P0 Quality Gates and Reliability Baseline
2. P1 Gateway and Auth Foundation
3. P2 Event Store and Projection Pipeline
4. P3 DOL and Rule Engine Completion
5. P4 Frontend Studio IDE Completion
6. P5 Service Boundary Full Split
7. P6 Security and Compliance Closure
8. P7 Observability and SRE Closure
9. P8 Deployment and DR Closure
10. P9 Performance Engineering Closure
11. P10 Test Matrix Full Closure

## P0 Quality Gates and Reliability Baseline

- [ ] P0-1 CI performance gate with hard thresholds
  - Files: `.github/workflows/perf-chaos-gate.yml`, `perf/k6_smoke.js`
  - Interfaces: CI job `perf-chaos` must fail on threshold breach
  - Tests: `tests/chaos/test_chaos_matrix.py`
  - Acceptance: PR pipeline fails when k6 checks or latency thresholds fail

- [ ] P0-2 Chaos gate beyond simple restart
  - Files: `perf/chaos_gate.sh`, `.github/workflows/perf-chaos-gate.yml`
  - Interfaces: restart matrix for `query-api`, `command-api`, `redis`, `neo4j`
  - Tests: `tests/chaos/test_chaos_matrix.py`
  - Acceptance: script validates service recovery and command/query health after matrix restarts

## P1 Gateway and Auth Foundation

- [ ] P1-1 Runtime API gateway layer
  - Files: `docker-compose.yml`, `k8s/*`, `helm/genesis-studio/templates/*`
  - Interfaces: gateway routes for `/api/query/*`, `/api/command/*`, rate-limit/auth policy
  - Tests: new `tests/contract/test_gateway_contract.py`
  - Acceptance: all traffic flows through gateway with policy enforcement

- [ ] P1-2 OAuth2/OIDC SSO and refresh-token flow
  - Files: `backend/security/auth.py`, `backend/command_app.py`, `backend/security/flask_auth.py`, `.env.example`
  - Interfaces: `/api/auth/authorize`, `/api/auth/callback`, `/api/auth/refresh`, `/api/auth/logout`
  - Tests: new `tests/security/test_oidc_flow.py`
  - Acceptance: external IdP login and refresh lifecycle pass with role mapping

## P2 Event Store and Projection Pipeline

- [ ] P2-1 Append-only event store abstraction
  - Files: `backend/async_bus/stream.py`, `backend/ontology/repository.py`, `backend/ontology/schemas.py`
  - Interfaces: event metadata with `correlation_id`, `causation_id`, `service`, `traceparent`
  - Tests: `tests/contract/test_rest_contract.py`, new `tests/contract/test_event_store_contract.py`
  - Acceptance: persisted events are queryable by transaction and correlation chains

- [ ] P2-2 Async projector worker with replay and lag metrics
  - Files: `backend/workers/tasks.py`, `backend/workers/celery_app.py`, `backend/command_app.py`
  - Interfaces: replay endpoint `/api/command/project/replay`, lag endpoint `/api/query/projections/lag`
  - Tests: new `tests/test_projection_replay.py`
  - Acceptance: projection rebuild from event stream succeeds and lag is measurable

## P3 DOL and Rule Engine Completion

- [ ] P3-1 OTD/LTD full constraint set and lifecycle hooks
  - Files: `backend/ontology/engine.py`, `backend/command_app.py`
  - Interfaces: validation responses include hook execution results
  - Tests: extend `tests/test_command_api.py`
  - Acceptance: full inheritance/interface/lifecycle constraints enforced at validation time

- [ ] P3-2 Migration runtime execution for `lazy`/`batch`/`dual-write`
  - Files: `backend/ontology/engine.py`, `backend/command_app.py`, `backend/ontology/repository.py`
  - Interfaces: `/api/command/ontology/migration/apply` reports execution stats and failures
  - Tests: new `tests/test_migration_execution.py`
  - Acceptance: mode-specific migration behavior executes real data updates

- [ ] P3-3 Distributed saga orchestration and compensation idempotency
  - Files: `backend/command_app.py`, `backend/workers/tasks.py`, `backend/ontology/repository.py`
  - Interfaces: saga state endpoint `/api/command/transactions/<txn_id>/saga`
  - Tests: new `tests/test_saga_orchestration.py`
  - Acceptance: multi-step compensation chain is idempotent and recoverable

## P4 Frontend Studio IDE Completion

- [ ] P4-1 Holy-Grail IDE tabs and domain panels
  - Files: `frontend/src/App.vue`, new `frontend/src/components/*`
  - Interfaces: Graph, Timeline, Logic, Inspector, Proposal tabs
  - Tests: new `frontend` component tests and `tests/e2e/test_studio_journey.py`
  - Acceptance: full tab workflow matches PRP sections 5 and 9

- [ ] P4-2 Proposal Card apply/reject/rollback UX flow
  - Files: `frontend/src/components/ProposalCard.vue`, `backend/command_app.py`
  - Interfaces: apply/reject endpoints with permission checks
  - Tests: new `tests/e2e/test_proposal_flow.py`
  - Acceptance: user can safely apply, reject, and rollback proposals from UI

## P5 Service Boundary Full Split

- [ ] P5-1 Split domain services and contracts
  - Files: new `backend/services/*`, `proto/*.proto`, `docker-compose.yml`, `k8s/*`
  - Interfaces: OntologyService/ObjectService/LinkService/TimeTravelService/SearchService/AuthService/NotificationService
  - Tests: new service contract tests per service
  - Acceptance: each service deploys and communicates through defined gRPC/HTTP contracts

## P6 Security and Compliance Closure

- [ ] P6-1 Immutable signed audit ledger
  - Files: `backend/ontology/repository.py`, new `backend/security/audit_signing.py`
  - Interfaces: signed hash chain verification endpoint `/api/query/audit/verify`
  - Tests: new `tests/security/test_audit_ledger.py`
  - Acceptance: tamper detection works on ledger verification

- [ ] P6-2 SOC2/GDPR operational APIs
  - Files: new `backend/routes/compliance.py`, `backend/app.py`
  - Interfaces: export/delete/process-record endpoints
  - Tests: new `tests/security/test_compliance_api.py`
  - Acceptance: export/delete workflow and audit evidence are generated

## P7 Observability and SRE Closure

- [ ] P7-1 Alert routing and SLO/SLA rules
  - Files: `observability/prometheus.yml`, new `observability/alerts.yaml`, `docker-compose.yml`
  - Interfaces: alert targets and rules for latency/error/availability
  - Tests: config validation and runtime firing simulation
  - Acceptance: alert rules trigger and route correctly under failure conditions

- [ ] P7-2 Runbook automation hooks
  - Files: new `ops/runbooks/*`, `.github/workflows/*`
  - Interfaces: scripted remediation entrypoints
  - Tests: runbook simulation scripts
  - Acceptance: critical incidents can be remediated via documented automation steps

## P8 Deployment and DR Closure

- [ ] P8-1 Full K8s and Helm topology
  - Files: `k8s/*`, `helm/genesis-studio/templates/*`, `helm/genesis-studio/values.yaml`
  - Interfaces: all services, dependencies, ingress, policy wiring
  - Tests: helm template validation and smoke deployment checks
  - Acceptance: full stack deploys on K8s from Helm with green health

- [ ] P8-2 GitOps/ArgoCD and DR drill automation
  - Files: new `argocd/*`, `dr/dr_plan.md`, new `dr/drill_scripts/*`
  - Interfaces: failover/failback workflow and drill reports
  - Tests: DR drill CI job
  - Acceptance: measured RPO/RTO evidence produced by automation

## P9 Performance Engineering Closure

- [ ] P9-1 Performance budget enforcement
  - Files: `perf/k6_smoke.js`, `.github/workflows/perf-chaos-gate.yml`
  - Interfaces: threshold policies for key APIs
  - Tests: CI gate execution
  - Acceptance: merge blocked when budget is exceeded

- [ ] P9-2 Multi-scenario benchmark suite
  - Files: new `perf/k6_*.js`, new `perf/playwright_*.ts`
  - Interfaces: batch scenarios for command/query/correlation lineage paths
  - Tests: CI perf suite job
  - Acceptance: benchmark report artifacts generated per PR/nightly

## P10 Test Matrix Full Closure

- [ ] P10-1 Pact consumer/provider contracts
  - Files: new `tests/pact/*`, `.github/workflows/ci.yml`
  - Interfaces: contract publishing/verification workflow
  - Tests: pact verify job
  - Acceptance: provider build fails on contract breakage

- [ ] P10-2 E2E journey and simulation matrix
  - Files: new `tests/e2e/*`
  - Interfaces: end-to-end user journey coverage for sections 9 and runtime simulation
  - Tests: e2e workflow job
  - Acceptance: journey scenarios pass in CI with artifacts

- [ ] P10-3 Expanded security and chaos matrix
  - Files: `.github/workflows/security-gate.yml`, `.github/workflows/perf-chaos-gate.yml`, `tests/chaos/*`, `tests/security/*`
  - Interfaces: blocking policy for security/chaos failures
  - Tests: matrix jobs
  - Acceptance: release path is blocked on any matrix failure
