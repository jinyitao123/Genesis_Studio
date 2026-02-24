# Genesis Studio PRP v3.0 Unimplemented Items Development Plan

## Scope Basis

- Reference: `Genesis_Studio_PRP_v3.0.md`
- Current implementation evidence: backend services, ABAC, gRPC runtime, observability stack, Docker/K8s/Helm/ArgoCD, contract/security/chaos tests.

## Unimplemented Items (Full Plan)

### A. Architecture and Service Boundaries
- API Gateway policy runtime (Kong/Envoy): auth/rate-limit/routing policies not wired as runtime gateway.
- Full Event Store + projector pipeline: append-only dedicated store and asynchronous read-model projection engine are still partial.
- Full DDD service split: Ontology/Object/Link/TimeTravel/Search/Auth/Notification are not independently deployed services.

### B. Dynamic Ontology Layer and Rule Engine
- Complete OTD/LTD constraints (interfaces, sealed inheritance enforcement, lifecycle hooks execution).
- Online schema migration runtime modes (`lazy`, `batch`, `dual-write`) with real data migration execution.
- Full Action pipeline L0-L4, Saga compensation orchestration, dry-run/revert transaction lineage.

### C. Frontend Studio IDE
- Full Holy-Grail IDE tabs and domain components (GraphVisualizer, TimelineController, LogicComposer, LineageGraph, proposal workflow UI).
- 10k-node WebGL/canvas performance implementation and UX journey completeness.

### D. Security and Compliance
- OAuth2/OIDC SSO integration with access+refresh token lifecycle.
- Immutable signed audit ledger and retention controls implementation.
- SOC2/GDPR operational workflows (export/delete/processing records).

### E. Observability and SRE
- Production dashboards and alert routing rules with SLA thresholds.
- Runbook automation with actionable remediation hooks.

### F. Deployment, DR, and Performance
- Full production K8s topology (all services + data plane components + service mesh policies).
- DR drills with verified RPO/RTO automation pipeline.
- Performance budget gates wired into CI with hard-fail thresholds.

### G. Testing Matrix Completion
- Pact-based consumer/provider contract workflow in CI.
- E2E journey tests for Studio UX and runtime simulation flow.
- Security scans (ZAP, Trivy) as blocking gates.
- Chaos engineering integration beyond script-level restart checks.

## Execution Plan (Ordered)

1. Complete quality/security gates in CI (type, tests, build, perf/chaos/security scan gates).
2. Finalize gateway and auth foundation (gateway manifests + OIDC/OAuth2 token flows).
3. Implement event-store/projector and action execution pipeline with transaction lineage.
4. Expand DOL migration/runtime semantics and ABAC externalized policy enforcement.
5. Build frontend IDE core components and end-to-end user journey workflows.
6. Finalize observability dashboards/alerts and DR/perf enforcement automation.
7. Validate complete matrix: unit/integration/contract/e2e/security/perf/chaos.

## Acceptance Criteria

- All PRP sections 2-14 have runtime evidence (code + test + deployment artifacts).
- CI blocks merge on quality/security/performance/contract failures.
- Docker and K8s paths both pass automated verification.
