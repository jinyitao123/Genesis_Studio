# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Full Operational Guide

`AGENTS.md` is the authoritative agent guide for this repo. Read it before any non-trivial task. It contains complete setup steps, CQRS boundary rules, naming conventions, error handling patterns, code style, and the mandatory Agent Completion Checklist.

## Essential Commands

```bash
# Backend tests
python -m pytest                                          # full suite
python -m pytest tests/test_command_api.py -x             # single file, fail-fast
python -m pytest tests/test_command_api.py::test_fn_name  # single test
python -m pytest tests/contract/ -x                       # contract tests

# Type check (must match CI)
python -m basedpyright backend tests run_grpc.py

# Frontend
cd frontend && npm ci && npm run build   # CI gate
cd frontend && npm run dev               # dev server (port 5173)

# Full stack
docker compose up -d --build
```

## Architecture

**CQRS + Event Sourcing.** All writes flow through Command API → Event Store → Celery Worker (projector) → read stores. Read handlers never write; write handlers never read from projection stores.

| Process | Tech | Port |
|---------|------|------|
| Gateway | Nginx | 18080 (integration test target) |
| Command API | FastAPI | 8000 (writes) |
| Query API | Flask | 5000 (reads) |
| gRPC | grpcio | 50051 |
| Frontend | Vue 3 + Vite | 5173 |

**Data stores:** Neo4j (graph topology), Redis (cache/broker), PostgreSQL (auth/event store), TimescaleDB (time-series), Elasticsearch (search/read model).

**Frontend stack:** Vue 3 `<script setup lang="ts">`, Pinia stores, `@vue-flow/core` + Cytoscape for graph views, `@/api/client.ts` for all HTTP calls (never raw `fetch()` in components).

### Key Paths

| Path | Purpose |
|------|---------|
| `backend/command_app.py` | FastAPI app (write path) |
| `backend/app.py` | Flask app (read path) |
| `backend/ontology/` | Ontology engine, schemas, repository |
| `backend/services/` | Shared services (object, ontology, auth, search…) |
| `backend/workers/` | Celery tasks / projectors |
| `backend/grpc/generated/` | Auto-generated protobuf stubs — **do not hand-edit** |
| `frontend/src/views/` | Page-level Vue components |
| `frontend/src/stores/` | Pinia stores (one per domain) |
| `frontend/src/api/client.ts` | Centralized API client |
| `tests/contract/` | Response-shape contract tests |
| `perf/` | k6 smoke tests + chaos gate |

## Current Development Target: OntoFlow Basic (PRP v1.1)

The active PRP is `PRP/Genesis_Studio_PRP.md`. It specifies a lightweight ontology editor UI with:

- **Ontology editing panel** (left sidebar 250px): create Classes, add Properties, define Relations, export Turtle/JSON-LD.
- **Graph workspace** (right 75%): create entity instances, drag-to-connect relations, CSV import/export, force-directed rendering via Cytoscape.
- **Persistent storage**: auto-save to `~/ontoflow/ontology.json` + `graph.json` within 500 ms; load on startup.

Backend ontology logic already exists in `backend/ontology/`. The frontend `useOntologyStore.ts` and `useGraphStore.ts` are the natural Pinia stores to extend. The existing `GraphView.vue` uses Cytoscape — reuse or extend it.

Route all API calls through the gateway (`/api/query/*` for reads, `/api/command/*` for writes). Do not bypass the gateway for integration tests.
