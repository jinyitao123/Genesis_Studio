# AGENTS.md

> Operational guidance for coding agents working in the **Genesis Studio** codebase.
> All architectural decisions must conform to **Genesis_Studio_PRP_v3.0.md**.

---

## 1. Project Shape

### Architecture

Genesis Studio follows a **CQRS + Event Sourcing** architecture with strict read/write path separation.

| Layer | Technology | Role |
|-------|-----------|------|
| **Gateway** | Nginx (Docker) | Reverse proxy, TLS termination, rate limiting |
| **Command API** | FastAPI (Python 3.11+) | Write path — Action dispatch, mutations |
| **Query API** | Flask (Blueprints) | Read path — Object hydration, search, projections |
| **Worker** | Celery + Redis Broker | Async tasks — projections, CDC sync, telemetry flush |
| **gRPC Service** | grpcio + protobuf | High-performance inter-service calls |
| **Frontend** | Vue 3 + TypeScript + Vite | Studio IDE SPA (`frontend/`) |

### Data Stores

| Store | Purpose | Access Pattern |
|-------|---------|---------------|
| **Neo4j** | Graph topology — nodes, edges, static properties | Read-heavy, Cypher queries |
| **Redis** | Cache (L1), distributed locks, Pub/Sub, Celery broker | Low-latency KV |
| **PostgreSQL** | Auth, RBAC/ABAC, audit log, event store | ACID writes |
| **TimescaleDB** | Time-series properties, telemetry | Append-heavy, tick-aligned |
| **Elasticsearch** | Full-text search, geo-spatial, soft-link resolution | CDC-synced read model |

### Infrastructure

- **Orchestration:** Docker Compose (dev), Kubernetes + Helm (staging/prod).
- **Observability:** OpenTelemetry SDK → Prometheus + Grafana + Loki + Tempo.
- **CI/CD:** GitHub Actions (lint → test → type-check → security → perf gate).

---

## 2. Rule File Precedence

| Priority | File | Status |
|----------|------|--------|
| 1 (highest) | `.cursor/rules/` or `.cursorrules` | Not present — create if needed |
| 2 | `.github/copilot-instructions.md` | Not present — create if needed |
| 3 (baseline) | This file (`AGENTS.md`) | **Active** |

If higher-priority rule files are added, they take precedence. Update this document to stay consistent.

---

## 3. Setup & Entrypoints

### 3.1 Python Environment

```bash
# Create venv (recommended)
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install type checker (must match CI)
pip install basedpyright
```

### 3.2 Frontend Environment

```bash
cd frontend && npm ci
```

### 3.3 Local Process Entrypoints

| Process | Command | Default Port |
|---------|---------|-------------|
| Query API (Flask) | `python run.py` | `5000` |
| Command API (FastAPI) | `python run_command.py` | `8000` |
| gRPC Service | `python run_grpc.py` | `50051` |
| Celery Worker | `celery -A backend.workers.celery_app.celery_app worker --loglevel=info` | — |
| Frontend Dev | `cd frontend && npm run dev` | `5173` |

### 3.4 Docker Compose

```bash
# Full stack (all services + infra + observability)
docker compose up -d --build

# App core only (faster iteration)
docker compose up -d --build gateway query-api command-api worker neo4j redis

# Diagnostics
docker compose ps                          # Service state
docker compose logs <service> --tail 200   # Recent logs
docker compose logs -f <service>           # Follow logs
```

---

## 4. Build / Lint / Test Commands

### 4.1 Type Checking

```bash
# Canonical command (must match CI exactly)
python -m basedpyright backend tests run_grpc.py
```

### 4.2 Backend Tests (pytest)

```bash
# Full suite
python -m pytest

# Fail-fast mode
python -m pytest -x

# Single file
python -m pytest tests/test_command_api.py

# Single test function
python -m pytest tests/test_command_api.py::test_command_endpoints

# Single contract test
python -m pytest tests/contract/test_rest_contract.py::test_projection_lag_contract_shape

# Pattern filter (e.g., all saga-related tests)
python -m pytest tests/test_command_api.py -k saga

# With coverage report
python -m pytest --cov=backend --cov-report=term-missing
```

### 4.3 Frontend

```bash
cd frontend
npm run build      # Production build (CI gate)
npm run dev        # Dev server with HMR
npm run preview    # Preview production build locally
```

### 4.4 Performance & Chaos Gates

```bash
# Chaos gate (requires Docker Compose running)
bash perf/chaos_gate.sh

# k6 smoke test
docker run --rm --network host \
  -v "$PWD/perf:/perf" grafana/k6:0.52.0 run /perf/k6_smoke.js
```

---

## 5. CI Pipeline Expectations

All local changes **must** pass these gates before push. The CI workflows are the source of truth.

### `ci.yml` — Backend

```yaml
steps:
  - pip install -r requirements.txt basedpyright
  - python -m basedpyright backend tests run_grpc.py
  - pytest
```

### `ci.yml` — Frontend

```yaml
steps:
  - npm ci
  - npm run build
```

### `perf-chaos-gate.yml`

```yaml
steps:
  - docker compose up -d --build
  - bash perf/chaos_gate.sh
  - k6 run perf/k6_smoke.js
```

### `security-gate.yml`

```yaml
steps:
  - Trivy image scan (CRITICAL/HIGH = fail)
  - ZAP baseline scan (WARN threshold)
```

---

## 6. Python Code Style

### 6.1 Module Header & Imports

```python
from __future__ import annotations

# 1. Standard library
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

# 2. Third-party
from fastapi import HTTPException
from pydantic import BaseModel

# 3. Project-local
from backend.services.object_service import ObjectService

if TYPE_CHECKING:
    from backend.models.ontology import ObjectTypeDefinition
```

- Always use `from __future__ import annotations` at module top.
- Explicit imports only — **no wildcard imports**.
- Guard heavy/circular imports with `TYPE_CHECKING`.

### 6.2 Typing & Models

- Modern unions: `str | None` (not `Optional[str]`).
- Built-in generics: `list[str]`, `dict[str, object]` (not `List`, `Dict`).
- Annotate **all** function parameters and return types.
- Use **Pydantic v2** models for all API request/response contracts.
- Serialize with `model_dump(mode="json")` for JSON responses.

### 6.3 Naming Conventions

| Scope | Convention | Example |
|-------|-----------|---------|
| Functions / variables | `snake_case` | `spawn_entity`, `link_uuid` |
| Classes / Pydantic models | `PascalCase` | `ObjectService`, `ActionRequest` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT`, `DEFAULT_TICK_RATE` |
| Endpoints | Action-oriented verbs | `list_entities`, `create_link`, `validate_schema`, `dispatch_action` |
| Secure endpoints | `*_secure` suffix | `list_entities_secure`, `get_topology_secure` |

### 6.4 Error Handling

```python
# FastAPI (Command API) — raise HTTPException at boundary
try:
    result = dispatcher.dispatch(request)
except InsufficientInventoryError as exc:
    raise HTTPException(status_code=409, detail=str(exc)) from exc
except EntityNotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc

# Flask (Query API) — return JSON tuple on auth failures
@app.route("/api/query/entities_secure")
def list_entities_secure():
    if not verify_token(request):
        return {"detail": "Authentication required"}, 401
```

- Convert internal exceptions at API boundary.
- Preserve cause chain with `raise ... from exc`.
- Never leak stack traces or internal paths in production error responses.

### 6.5 Resource & Observability Patterns

```python
# Always close repository objects in finally blocks
repo = GitRepository(path)
try:
    schema = repo.load_schema(commit_hash)
finally:
    repo.close()

# Record HTTP metrics in every handler
record_http_request(path="/api/command/dispatch", status=response.status_code)

# Apply ABAC filtering on secure read endpoints
entities = filter_read_fields(entities, user_role, user_permissions)
```

### 6.6 Time Handling

- **Always** use UTC-aware timestamps: `datetime.now(timezone.utc)`.
- API payloads and storage fields use ISO 8601 format: `2026-02-11T14:30:00Z`.
- Simulation ticks are integers; wall-clock timestamps are ISO strings.

### 6.7 CQRS Boundary Discipline

- **Command API (FastAPI):** Handles all write operations. Receives `ActionRequest`, dispatches to `ActionDispatcher`, writes to Event Store. **Never** reads from projection stores (Neo4j/ES) in write handlers.
- **Query API (Flask):** Handles all read operations. Reads from projection stores (Neo4j, ES, TimescaleDB, Redis cache). **Never** writes to Event Store in read handlers.
- **Worker (Celery):** Consumes events from Event Store / Redis Streams, updates read model projections. Idempotent task design — safe to retry.
- Violating CQRS boundaries is a **critical architecture error**. If a command handler needs current state for validation, it reads via `ObjectService` (which is a read-side service used internally by the dispatcher).

---

## 7. Frontend Style

### 7.1 Component Conventions

```vue
<script setup lang="ts">
// Use Composition API exclusively
import { ref, computed, onMounted } from 'vue'
import type { EntityDTO } from '@/types/entity'

const entities = ref<EntityDTO[]>([])
const activeCount = computed(() => entities.value.filter(e => e.status === 'active').length)
</script>
```

- All Vue SFCs use `<script setup lang="ts">`.
- State in `ref()`, derivations in `computed()`.
- Component files: `PascalCase.vue` in `frontend/src/components/`.
- Page/view files: `PascalCase.vue` in `frontend/src/views/`.

### 7.2 API Communication

- Type all API payloads with local `type` aliases or shared types from `@/types/`.
- Use a centralized API client (`@/api/client.ts`) — never raw `fetch()` in components.
- Command endpoints → `POST /api/command/*`.
- Query endpoints → `GET /api/query/*`.
- Auth endpoints → `POST /api/auth/*`.

### 7.3 Responsive Design

- Mobile-first with Tailwind breakpoints.
- Media-query fallback for narrow screens (< 768px: collapse sidebars, stack panels).
- Canvas components (Cytoscape, Vue Flow) must handle resize events.

---

## 8. Testing Style

### 8.1 General Principles

- **Framework:** `pytest` for all backend, contract, security, and chaos tests.
- **Isolation:** Use `monkeypatch.setattr` / `monkeypatch.setenv` for deterministic isolation. No shared mutable state between tests.
- **Naming:** Test files mirror source: `backend/services/foo.py` → `tests/test_foo.py`. Test functions: `test_<behavior>_<condition>_<expectation>`.

### 8.2 API Test Clients

| API | Client | Example |
|-----|--------|---------|
| Command API (FastAPI) | `fastapi.testclient.TestClient` | `client = TestClient(app)` |
| Query API (Flask) | `app.test_client()` | `client = app.test_client()` |

### 8.3 Contract Tests

- Assert **explicit response shape keys** (not just status codes).
- Contract tests live in `tests/contract/`.
- Verify projection lag contracts, event schema contracts, and API response shapes.

### 8.4 Test Categories

| Category | Directory | Runs In |
|----------|----------|---------|
| Unit | `tests/` | `pytest` (CI) |
| Contract | `tests/contract/` | `pytest` (CI) |
| Security | `tests/security/` | `pytest` (CI) + ZAP (security gate) |
| Performance | `perf/` | k6 + chaos_gate (perf gate) |

---

## 9. Gateway & Routing

### Route Map

| Prefix | Backend | Purpose |
|--------|---------|---------|
| `/api/query/*` | Query API (Flask) | Read operations — entities, topology, search, history |
| `/api/command/*` | Command API (FastAPI) | Write operations — action dispatch, entity mutations |
| `/api/auth/*` | Command API (FastAPI) | Authentication — login, token refresh, RBAC |
| `/ws/*` | Notification Service | WebSocket — real-time updates, telemetry push |

### Validation Rules

- Gateway base URL: `http://localhost:18080` (Docker Compose).
- **Always validate route changes through the gateway**, not only direct service ports.
- Direct service ports (5000, 8000) are for debugging only — not for integration testing.

---

## 10. Sensitive & Generated Areas

### Do Not Hand-Edit

| Path | Reason |
|------|--------|
| `backend/grpc/generated/*` | Auto-generated protobuf stubs. Regenerate with `make proto` or equivalent. |
| `pyrightconfig.json` exclusions | Keep `generated/` excluded — do not remove. |

### Security

- **Never** commit real credentials. `.env.example` is a template only.
- Secrets are injected via environment variables or Vault in deployment.
- API keys, database passwords, JWT signing keys must be in `.env` (gitignored) or Vault.

---

## 11. Agent Completion Checklist

Before marking any task as complete, execute **every applicable step** in order:

```
┌─────────────────────────────────────────────────────────────┐
│                  AGENT COMPLETION CHECKLIST                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  □ 1. Run targeted test(s) for touched behavior             │
│       python -m pytest tests/test_<touched>.py -x           │
│                                                             │
│  □ 2. Run full backend test suite                           │
│       python -m pytest                                      │
│                                                             │
│  □ 3. Run type checker                                      │
│       python -m basedpyright backend tests run_grpc.py      │
│                                                             │
│  □ 4. If frontend touched: build check                      │
│       cd frontend && npm run build                          │
│                                                             │
│  □ 5. If routing/infra touched: gateway validation          │
│       curl http://localhost:18080/api/query/health           │
│       curl http://localhost:18080/api/command/health         │
│                                                             │
│  □ 6. If schema/model changed: contract test                │
│       python -m pytest tests/contract/ -x                   │
│                                                             │
│  □ 7. Update tests when behavior changes                    │
│                                                             │
│  □ 8. Update docs (AGENTS.md, docstrings, README)           │
│       when public API or workflow changes                    │
│                                                             │
│  □ 9. Verify no secrets or generated code in diff           │
│       git diff --cached --name-only | grep -E               │
│         '\.env$|generated/|secret|password|key'             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Severity of Failures

| Step | Failure Severity | Action |
|------|-----------------|--------|
| 1-3 | **Blocking** | Must fix before commit |
| 4-5 | **Blocking** (if applicable) | Must fix before commit |
| 6 | **High** | Fix or document exception |
| 7-8 | **Medium** | Should fix in same PR |
| 9 | **Critical** | Immediate revert if missed |

---

## 12. Common Pitfalls

| Pitfall | Consequence | Prevention |
|---------|------------|------------|
| Writing to Neo4j in a Query API handler | CQRS violation — inconsistent read model | All writes go through Command API → Event Store → Projector |
| Using `datetime.now()` without timezone | Naive timestamps cause tick misalignment | Always `datetime.now(timezone.utc)` |
| Editing `backend/grpc/generated/*` | Changes overwritten on next proto gen | Edit `.proto` files, then regenerate |
| Testing against direct service port | Misses gateway routing/auth issues | Test through `localhost:18080` for integration |
| Wildcard imports (`from x import *`) | Namespace pollution, type-check evasion | Explicit imports only |
| Missing `from __future__ import annotations` | Runtime type errors with forward refs | Required at top of every module |
| Committing `.env` with real secrets | Credential leak | `.env` is gitignored; use `.env.example` as template |
| Non-idempotent Celery tasks | Duplicate projections on retry | Design tasks idempotent (check-then-write, upsert) |