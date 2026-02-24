storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = "true"
}

disable_mlock = true

api_addr      = "http://0.0.0.0:8200"
cluster_addr  = "http://127.0.0.1:8201"
ui            = true

max_lease_ttl = "87600h"
default_lease_ttl = "87600h"

plugin_directory = "/vault/plugins"
