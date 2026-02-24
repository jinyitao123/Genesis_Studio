#!/bin/bash
# Vault Initialization Script for Genesis Studio
# This script initializes Vault with required secrets and policies

set -e

export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="vault-dev-token"

echo "=== Genesis Studio Vault Initialization ==="
echo ""

# Wait for Vault to be ready
echo "Waiting for Vault to be ready..."
sleep 5

# Enable required secrets engines
echo "Enabling secrets engines..."
vault secrets enable -path=secret -version=2 kv 2>/dev/null || echo "Secret engine already enabled"
vault secrets enable -path=database database 2>/dev/null || echo "Database engine already enabled"
vault secrets enable -path=transit -type=transit transit 2>/dev/null || echo "Transit engine already enabled"

# Enable Kubernetes auth
echo "Enabling Kubernetes auth..."
vault auth enable kubernetes 2>/dev/null || echo "Kubernetes auth already enabled"

# Write application secrets
echo "Writing application secrets..."
vault kv put secret/genesis/neo4j \
  uri="bolt://neo4j:7687" \
  user="neo4j" \
  password="${NEO4J_PASSWORD:-neo4j_password}" 2>/dev/null || echo "Neo4j secrets already exist"

vault kv put secret/genesis/redis \
  url="redis://redis:6379/0" 2>/dev/null || echo "Redis secrets already exist"

vault kv put secret/genesis/jwt \
  secret="${JWT_SECRET:-genesis-jwt-secret-change-in-production}" \
  algorithm="HS256" 2>/dev/null || echo "JWT secrets already exist"

# Configure database dynamic secrets
echo "Configuring database dynamic secrets..."
vault write database/config/genesis-postgres \
  plugin_name=postgresql-database-plugin \
  connection_url="postgres://postgres:postgres@postgres:5432/genesis?sslmode=disable" \
  allowed_roles="genesis-role" 2>/dev/null || echo "Database config already exists"

vault write database/roles/genesis-role \
  db_name=genesis-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h" 2>/dev/null || echo "Database role already exists"

# Configure transit key for audit signing
echo "Configuring transit key..."
vault write -f transit/keys/audit-signing \
  type="rsa-2048" 2>/dev/null || echo "Transit key already exists"

# Create and apply policies
echo "Creating policies..."
vault policy write genesis-app /vault/policies/genesis-app-policy.hcl 2>/dev/null || echo "Policy already exists"

# Configure Kubernetes auth
echo "Configuring Kubernetes auth..."
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc:443" \
  kubernetes_ca_cert="@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt" \
  token_reviewer_jwt="@/var/run/secrets/kubernetes.io/serviceaccount/token" 2>/dev/null || echo "Kubernetes config already exists"

# Create Kubernetes auth role
vault write auth/kubernetes/role/genesis-app \
  bound_service_account_names="genesis-app" \
  bound_service_account_namespaces="genesis" \
  policies="genesis-app" \
  ttl="1h" 2>/dev/null || echo "Kubernetes role already exists"

echo ""
echo "=== Vault Initialization Complete ==="
echo ""
echo "Application secrets are now available at:"
echo "  - secret/genesis/neo4j"
echo "  - secret/genesis/redis"
echo "  - secret/genesis/jwt"
echo ""
echo "Database dynamic credentials available at:"
echo "  - database/creds/genesis-role"
echo ""
echo "Transit key for audit signing:"
echo "  - transit/keys/audit-signing"
echo ""
echo "Vault UI available at: http://localhost:18200"
echo "Token: vault-dev-token"
