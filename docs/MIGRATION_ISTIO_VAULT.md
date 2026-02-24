# Genesis Studio Migration Guide

## Phase 1: Istio Service Mesh + HashiCorp Vault Integration

This document describes the migration from the current nginx-based infrastructure to Istio service mesh with HashiCorp Vault for secrets management.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Changes](#architecture-changes)
4. [Migration Steps](#migration-steps)
5. [Rollback Procedure](#rollback-procedure)
6. [Verification](#verification)

---

## Overview

### Current State
- **API Gateway**: Nginx reverse proxy with basic rate limiting
- **Secrets Management**: Environment variables in `.env` files
- **Service Communication**: Direct DNS resolution
- **Security**: JWT-based authentication only

### Target State
- **API Gateway**: Istio Ingress Gateway with mTLS
- **Secrets Management**: HashiCorp Vault with dynamic secrets
- **Service Communication**: mTLS between all services
- **Security**: Zero-trust network with NetworkPolicies

---

## Prerequisites

### Tools Required
- Kubernetes CLI (`kubectl`) v1.28+
- Helm v3.12+
- Istio CLI (`istioctl`) v1.20+
- Vault CLI v1.15+
- Docker and Docker Compose

### Cluster Requirements
- Kubernetes cluster v1.28+
- Minimum 3 worker nodes
- 16GB RAM per node
- 100GB storage per node

---

## Architecture Changes

### Before: Nginx Gateway
```
Internet → Nginx (port 18080) → Services
```

### After: Istio Gateway
```
Internet → Istio Ingress Gateway (443/80) → Services (mTLS)
```

### Network Segmentation
```
# Before: Flat network
All pods → All pods (no restrictions)

# After: Zero-trust network
Pod → Only allowed destinations (via NetworkPolicy)
```

---

## Migration Steps

### Step 1: Install Istio

```bash
# Download and install istioctl
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.20.0
export PATH=$PWD/bin:$PATH

# Install Istio with demo profile
istioctl install --set profile=demo -y

# Enable automatic sidecar injection
kubectl label namespace genesis istio-injection=enabled
```

### Step 2: Install HashiCorp Vault

```bash
# Add HashiCorp Helm repository
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# Install Vault with Helm
helm install vault hashicorp/vault \
  --namespace vault \
  --create-namespace \
  --set "server.dev.devRootToken=vault-dev-token" \
  --set "server.dev.enabled=true"
```

### Step 3: Deploy Istio Resources

```bash
# Deploy Istio Gateway, VirtualServices, and DestinationRules
kubectl apply -f helm/genesis-studio/templates/istio/

# Verify deployment
kubectl get gateway -n genesis
kubectl get virtualservice -n genesis
kubectl get destinationrule -n genesis
```

### Step 4: Deploy NetworkPolicies

```bash
# Apply NetworkPolicies for zero-trust network
kubectl apply -f helm/genesis-studio/templates/network/
```

### Step 5: Initialize Vault

```bash
# Start Vault init container
kubectl apply -f vault-init-job.yaml

# Or use docker-compose for local development
docker-compose up vault vault-init -d

# Access Vault UI
# Open http://localhost:18200
# Token: vault-dev-token
```

### Step 6: Deploy Application with Vault Agent

```bash
# Deploy services with Vault Agent sidecar
kubectl apply -f helm/genesis-studio/templates/secrets/
kubectl apply -f helm/genesis-studio/templates/deployment-*.yaml

# Verify pods have Vault Agent running
kubectl get pods -n genesis -l app=query-api
kubectl exec -n genesis deployment/query-api -c vault-agent -- vault status
```

### Step 7: Switch DNS

```bash
# Update DNS to point to Istio Ingress Gateway
# In your DNS provider or /etc/hosts:
# genesis.studio → Istio Ingress Gateway IP

# Verify Istio Ingress Gateway IP
kubectl get svc -n istio-system istio-ingressgateway
```

### Step 8: Enable mTLS

```bash
# Enable STRICT mTLS for all services
kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: genesis
spec:
  mtls:
    mode: STRICT
EOF
```

---

## Rollback Procedure

### Rollback to Nginx

```bash
# 1. Switch DNS back to Nginx
# Update DNS to point to nginx service IP

# 2. Disable Istio sidecar injection
kubectl label namespace genesis istio-injection-

# 3. Restart pods to remove sidecars
kubectl rollout restart deployment -n genesis

# 4. Remove Istio resources
kubectl delete -f helm/genesis-studio/templates/istio/

# 5. Remove NetworkPolicies
kubectl delete -f helm/genesis-studio/templates/network/

# 6. Keep Vault running for future migration
```

### Rollback Secrets to Environment Variables

```bash
# 1. Update deployments to use env vars instead of Vault secrets
kubectl set env deployment/command-api NEO4J_URI="bolt://neo4j:7687" -n genesis
kubectl set env deployment/command-api NEO4J_USER="neo4j" -n genesis
kubectl set env deployment/command-api NEO4J_PASSWORD="${NEO4J_PASSWORD}" -n genesis

# 2. Remove Vault Agent annotations
kubectl annotate deployment command-api vault.hashicorp.com/agent-inject- -n genesis

# 3. Restart pods
kubectl rollout restart deployment -n genesis
```

---

## Verification

### Check Istio Configuration

```bash
# Verify Gateway
kubectl get gateway -n genesis -o yaml

# Verify VirtualServices
kubectl get virtualservice -n genesis

# Check mTLS status
istioctl x authz check deployment/query-api -n genesis
```

### Check Vault Integration

```bash
# Check Vault Agent logs
kubectl logs -n genesis deployment/query-api -c vault-agent

# Verify secrets are mounted
kubectl exec -n genesis deployment/query-api -- cat /vault/secrets/secrets.yml

# Check Vault status
vault status
```

### Check Network Policies

```bash
# Verify NetworkPolicies are applied
kubectl get networkpolicy -n genesis

# Test connectivity
kubectl exec -n genesis deployment/query-api -- curl -s http://command-api:8000/health
```

### Check mTLS

```bash
# Verify service-to-service mTLS
istioctl x get verify-install -n genesis

# Check certificate rotation
kubectl get cm istio -n istio-system -o yaml | grep certResource
```

---

## Monitoring

### Prometheus Metrics

```bash
# Access Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Key metrics:
# - istio_requests_total (mTLS traffic)
# - istio_tcp_received_bytes (service communication)
# - vault_secret_sync_total (Vault agent)
```

### Grafana Dashboards

```bash
# Access Grafana
kubectl port-forward -n istio-system svc/grafana 3000:3000

# Import Istio dashboards:
# - Istio Service Dashboard
# - Istio Workload Dashboard
# - Vault Audit Log Dashboard
```

---

## Troubleshooting

### Common Issues

#### Issue: Pods not starting with Vault Agent
```bash
# Check Vault Agent logs
kubectl logs -n genesis deployment/query-api -c vault-agent

# Verify Vault connectivity
kubectl exec -n genesis deployment/query-api -- curl -s https://vault.vault.svc.cluster.local:8200/v1/sys/health
```

#### Issue: mTLS not working
```bash
# Check PeerAuthentication
kubectl get peerauthentication -n genesis -o yaml

# Verify Istio sidecar is injected
kubectl get pods -n genesis -l app=query-api -o jsonpath='{.items[0].spec.containers[*].name}'
```

#### Issue: NetworkPolicy blocking traffic
```bash
# Check applied policies
kubectl describe networkpolicy genesis-allow-query-api -n genesis

# Temporarily disable for testing
kubectl delete networkpolicy genesis-allow-query-api -n genesis
```

---

## Security Considerations

### Production Checklist

- [ ] Enable STRICT mTLS for all namespaces
- [ ] Use production Vault unseal keys
- [ ] Enable Vault audit logging
- [ ] Configure NetworkPolicies for all namespaces
- [ ] Enable Istio mutual TLS for all services
- [ ] Use cert-manager for TLS certificate rotation
- [ ] Configure RBAC for Kubernetes resources
- [ ] Enable Istio rate limiting

### Best Practices

1. **Secrets Rotation**: Rotate database credentials every 24 hours
2. **Certificate Rotation**: Istio certificates rotate automatically every 24 hours
3. **Audit Logging**: Enable comprehensive audit logging in Vault
4. **Network Segmentation**: Apply least-privilege NetworkPolicies
5. **Monitoring**: Set up alerts for security events

---

## Additional Resources

- [Istio Documentation](https://istio.io/latest/docs/)
- [Vault Documentation](https://developer.hashicorp.com/vault/docs)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Zero Trust Architecture](https://www.nist.gov/publications/zero-trust-architecture)

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs: `kubectl logs -n genesis <pod-name>`
3. Check Istio logs: `kubectl logs -n istio-system -l app=istio-ingressgateway`
4. Contact the platform team
