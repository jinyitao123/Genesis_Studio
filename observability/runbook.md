# Genesis Studio Runbook

## Neo4j unavailable
1. `docker compose logs neo4j`.
2. Verify health check command and credentials.
3. Restart with `docker compose restart neo4j`.

## Redis backlog
1. Check worker health with `docker compose logs worker`.
2. Verify stream growth in `genesis:domain-events`.
3. Scale worker replicas in deployment layer.

## Command API latency spike
1. Check `/metrics` counters and endpoint status.
2. Validate Neo4j and Redis readiness.
3. Reduce batch size and re-run migration in batch mode.
