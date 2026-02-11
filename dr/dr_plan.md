# Disaster Recovery Plan (Baseline)

## Objectives
- RPO: < 1 minute (event stream + db snapshots)
- RTO: < 5 minutes (compose/k8s restore path)

## Recovery Steps
1. Confirm failure scope and isolate failed services.
2. Restore Neo4j and Postgres from latest snapshots.
3. Start command/query APIs and worker.
4. Rebuild projection via `/api/command/project`.
5. Validate health endpoints and projection consistency.

## Verification
- `GET /api/health` returns 200.
- `GET /health` returns 200.
- `GET /api/query/projections/latest` returns non-empty projection.
