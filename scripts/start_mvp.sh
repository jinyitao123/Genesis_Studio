#!/usr/bin/env bash
set -euo pipefail

services=(
  frontend
  gateway
  query-api
  command-api
  worker
  grpc-api
  neo4j
  redis
  postgres
)

docker compose up -d --build "${services[@]}"

echo "Genesis Studio MVP is starting."
echo "Gateway: http://localhost:18080"
echo "Frontend direct: http://localhost:5173"
echo "Grafana: http://localhost:13000"
