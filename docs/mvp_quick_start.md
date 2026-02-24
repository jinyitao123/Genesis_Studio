# Genesis Studio MVP Quick Start

## One-click startup

- PowerShell (Windows): `./scripts/start_mvp.ps1`
- Bash (Linux/macOS): `bash ./scripts/start_mvp.sh`

This boots frontend, gateway, query-api, command-api, worker, grpc-api, neo4j, redis, postgres.

## Access points

- Unified gateway + frontend: `http://localhost:18080`
- Frontend direct dev server: `http://localhost:5173`
- Query API via gateway: `http://localhost:18080/api/query/*`
- Command API via gateway: `http://localhost:18080/api/command/*`
- Compliance API via gateway: `http://localhost:18080/api/compliance/*`
