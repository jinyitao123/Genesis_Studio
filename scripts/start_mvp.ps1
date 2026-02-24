$ErrorActionPreference = "Stop"

$services = @(
  "frontend",
  "gateway",
  "query-api",
  "command-api",
  "worker",
  "grpc-api",
  "neo4j",
  "redis",
  "postgres"
)

docker compose up -d --build $services

Write-Host "Genesis Studio MVP is starting."
Write-Host "Gateway: http://localhost:18080"
Write-Host "Frontend direct: http://localhost:5173"
Write-Host "Grafana: http://localhost:13000"
