# Microservice Boundaries

# gateway (nginx)
- Responsibility: ingress routing for query/command/auth/copilot paths.
- Endpoints: `/api/query/*`, `/api/command/*`, `/api/auth/*`, `/api/copilot/*`, `/health`, `/metrics` via gateway port `18080`.

## query-api (Flask)
- Responsibility: read-side projection queries and health/metrics.
- Endpoints: `/api/query/*`, `/api/query/projections/lag`, `/api/health*`, `/api/metrics`.

## command-api (FastAPI)
- Responsibility: write-side commands, ontology validation/migration, copilot routing.
- Endpoints: `/api/command/*`, `/api/command/project/replay`, `/api/command/transactions/{txn_id}/saga`, `/api/command/proposals*`, `/api/command/services/ontology/validate`, `/api/command/services/object/upsert`, `/api/command/services/link/connect`, `/api/command/services/time-travel/snapshot`, `/api/command/services/search`, `/api/command/services/auth/issue-token`, `/api/command/services/notification/publish`, `/api/auth/token`, `/api/auth/token/pair`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/oidc/*`, `/api/copilot/route`, `/metrics`.

## grpc-api (gRPC)
- Responsibility: internal projection operation surface.
- Service: `CommandProjectionService` with `Health` and `CreateProjection` RPCs plus trailing metadata (`x-genesis-service`, `x-genesis-operation`, `x-genesis-status`).

## domain service contracts (P5 foundation)
- Contract file: `proto/genesis_domain_services.proto`.
- Declared services: `OntologyService`, `ObjectService`, `LinkService`, `TimeTravelService`, `SearchService`, `AuthService`, `NotificationService`.
- Python interface stubs: `backend/services/*.py`.

## worker (Celery)
- Responsibility: async projection refresh and background tasks.
- Queue backend: Redis.

## observability plane
- Components: OpenTelemetry Collector, Tempo, Loki, Prometheus, Grafana.
- Signals: traces (OTLP->Tempo), metrics (HTTP scrape), logs pipeline prepared for Loki.
