#!/bin/bash
# Vault Setup Script for Tasks API
# This script deploys Vault to Kubernetes and configures it for the tasks-api application.
#
# Usage:
#   Development: ./setup-vault.sh dev
#   Production:  ./setup-vault.sh prod
#
# Prerequisites:
#   - kubectl configured with cluster access
#   - helm installed
#   - HashiCorp Vault Helm repo added: helm repo add hashicorp https://helm.releases.hashicorp.com

set -e

MODE="${1:-dev}"
VAULT_NAMESPACE="tasks-api"
BACKEND_NAMESPACE="${BACKEND_NAMESPACE:-default}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Vault Setup for Tasks API ==="
echo "Mode: $MODE"
echo "Vault Namespace: $VAULT_NAMESPACE"
echo "Backend Namespace: $BACKEND_NAMESPACE"
echo ""

# Add HashiCorp Helm repo
echo "Adding HashiCorp Helm repository..."
helm repo add hashicorp https://helm.releases.hashicorp.com 2>/dev/null || true
helm repo update

# Create vault namespace
kubectl create namespace "$VAULT_NAMESPACE" 2>/dev/null || true

# Install Vault based on mode
if [ "$MODE" = "dev" ]; then
    echo "Installing Vault in DEVELOPMENT mode..."
    helm upgrade --install vault hashicorp/vault \
        -f "$SCRIPT_DIR/vault-helm-values-dev.yaml" \
        -n "$VAULT_NAMESPACE" \
        --wait

    VAULT_TOKEN="dev-root-token"
    echo "Using dev root token: $VAULT_TOKEN"
else
    echo "Installing Vault in PRODUCTION mode..."
    helm upgrade --install vault hashicorp/vault \
        -f "$SCRIPT_DIR/vault-helm-values.yaml" \
        -n "$VAULT_NAMESPACE" \
        --wait

    # Wait for pod to be ready
    echo "Waiting for Vault pod..."
    kubectl wait --for=condition=Ready pod/vault-0 -n "$VAULT_NAMESPACE" --timeout=300s || true

    # Check if initialized
    INIT_STATUS=$(kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- vault status -format=json 2>/dev/null | jq -r '.initialized' || echo "false")

    if [ "$INIT_STATUS" = "false" ]; then
        echo ""
        echo "Vault needs to be initialized. Run:"
        echo "  kubectl exec -n $VAULT_NAMESPACE vault-0 -- vault operator init"
        echo ""
        echo "Then unseal with the keys and re-run this script with VAULT_TOKEN set."
        exit 0
    fi

    if [ -z "$VAULT_TOKEN" ]; then
        echo "Please set VAULT_TOKEN environment variable with your root/admin token."
        exit 1
    fi
fi

# Wait for Vault to be ready
echo "Waiting for Vault to be ready..."
sleep 5
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=vault -n "$VAULT_NAMESPACE" --timeout=120s

# Configure Vault
echo "Configuring Vault..."

# Enable KV secrets engine
echo "Enabling KV secrets engine..."
kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" \
    vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV secrets engine already enabled"

# Enable Kubernetes auth
echo "Enabling Kubernetes auth..."
kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" \
    vault auth enable kubernetes 2>/dev/null || echo "Kubernetes auth already enabled"

# Configure Kubernetes auth
echo "Configuring Kubernetes auth..."
kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- sh -c "
    VAULT_TOKEN='$VAULT_TOKEN' vault write auth/kubernetes/config \
        kubernetes_host='https://\$KUBERNETES_PORT_443_TCP_ADDR:443'
"

# Create the tasks-api policy
echo "Creating tasks-api policy..."
kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" sh -c '
cat <<EOF | vault policy write tasks-api -
path "secret/data/tasks-api/*" {
  capabilities = ["read"]
}
path "secret/metadata/tasks-api/*" {
  capabilities = ["list"]
}
EOF
'

# Create ServiceAccount for tasks-api
echo "Creating ServiceAccount for tasks-api..."
kubectl create namespace "$BACKEND_NAMESPACE" 2>/dev/null || true
kubectl create serviceaccount tasks-api -n "$BACKEND_NAMESPACE" 2>/dev/null || echo "ServiceAccount already exists"

# Create Kubernetes auth role
echo "Creating Kubernetes auth role..."
kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" \
    vault write auth/kubernetes/role/tasks-api \
        bound_service_account_names=tasks-api \
        bound_service_account_namespaces="$BACKEND_NAMESPACE" \
        policies=tasks-api \
        ttl=1h

# Add sample secrets for development
if [ "$MODE" = "dev" ]; then
    echo ""
    echo "Adding sample secrets for development..."
    kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" \
        vault kv put secret/tasks-api/database \
            database_url="postgresql://postgres:postgres@postgres:5432/tasksdb"

    kubectl exec -n "$VAULT_NAMESPACE" vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" \
        vault kv put secret/tasks-api/auth \
            secret_key="dev-secret-key-$(openssl rand -hex 16)"
fi

echo ""
echo "=== Vault Setup Complete ==="
echo ""
echo "Vault UI: kubectl port-forward svc/vault -n $VAULT_NAMESPACE 8200:8200"
if [ "$MODE" = "dev" ]; then
    echo "Dev Token: $VAULT_TOKEN"
fi
echo ""
echo "To add/update secrets:"
echo "  kubectl exec -n $VAULT_NAMESPACE vault-0 -- env VAULT_TOKEN='$VAULT_TOKEN' \\"
echo "      vault kv put secret/tasks-api/database database_url='your-db-url'"
echo ""
echo "  kubectl exec -n $VAULT_NAMESPACE vault-0 -- env VAULT_TOKEN='$VAULT_TOKEN' \\"
echo "      vault kv put secret/tasks-api/auth secret_key='your-secret-key'"
echo ""
echo "To verify secrets:"
echo "  kubectl exec -n $VAULT_NAMESPACE vault-0 -- env VAULT_TOKEN='$VAULT_TOKEN' \\"
echo "      vault kv get secret/tasks-api/database"
echo ""
echo "Deploy backend with Vault:"
echo "  helm install tasks-api ./backend/helm -n $BACKEND_NAMESPACE"
