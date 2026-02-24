# Genesis Studio Application Policy
# Grants read access to required secrets

# Application secrets
path "secret/genesis/neo4j" {
  capabilities = ["read", "list"]
}

path "secret/genesis/redis" {
  capabilities = ["read", "list"]
}

path "secret/genesis/jwt" {
  capabilities = ["read", "list"]
}

# Database dynamic credentials
path "database/creds/genesis-role" {
  capabilities = ["read"]
}

# Transit keys for audit signing
path "transit/keys/audit-signing" {
  capabilities = ["read", "sign"]
}

# Transit signing operations
path "transit/sign/*" {
  capabilities = ["update"]
}
