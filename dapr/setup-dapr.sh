#!/bin/bash
# Dapr Setup Script for Tasks API
# This script deploys Dapr to Kubernetes using the official Helm chart.
# Dapr runs as a control plane in the "dapr-system" namespace and injects
# sidecar containers into your application pods automatically.
#
# Usage:
#   Development: ./setup-dapr.sh dev
#   Production:  ./setup-dapr.sh prod
#
# Prerequisites:
#   - kubectl configured with cluster access
#   - helm installed

set -e

MODE="${1:-dev}"
DAPR_NAMESPACE="${DAPR_NAMESPACE:-dapr-system}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Dapr Setup for Tasks API ==="
echo "Mode: $MODE"
echo "Namespace: $DAPR_NAMESPACE"
echo ""

# Add Dapr Helm repo
# This is the official Helm chart maintained by the Dapr project.
# It installs 3 components:
#   - dapr-operator: manages Dapr component CRDs (like our kafka-pubsub.yaml)
#   - dapr-sentry: handles mTLS certificates between sidecars
#   - dapr-sidecar-injector: watches for pods with dapr.io/enabled annotation
echo "Adding Dapr Helm repository..."
helm repo add dapr https://dapr.github.io/helm-charts/ 2>/dev/null || true
helm repo update

# Create namespace for Dapr control plane
kubectl create namespace "$DAPR_NAMESPACE" 2>/dev/null || true

# Install Dapr based on mode
if [ "$MODE" = "dev" ]; then
    echo "Installing Dapr in DEVELOPMENT mode..."
    echo "  - Single replica per component (no HA)"
    echo "  - JSON logging for easier debugging"
    helm upgrade --install dapr dapr/dapr \
        -f "$SCRIPT_DIR/dapr-helm-values-dev.yaml" \
        -n "$DAPR_NAMESPACE" \
        --wait
else
    echo "Installing Dapr in PRODUCTION mode..."
    echo "  - HA enabled (3 replicas per component)"
    echo "  - Higher resource limits"
    helm upgrade --install dapr dapr/dapr \
        -f "$SCRIPT_DIR/dapr-helm-values-prod.yaml" \
        -n "$DAPR_NAMESPACE" \
        --wait
fi

# Wait for all Dapr pods to be ready
echo "Waiting for Dapr pods to be ready..."
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/part-of=dapr \
    -n "$DAPR_NAMESPACE" --timeout=120s

echo ""
echo "=== Dapr Setup Complete ==="
echo ""
echo "Dapr control plane pods:"
kubectl get pods -n "$DAPR_NAMESPACE"
echo ""
echo "Dapr version:"
kubectl get pods -n "$DAPR_NAMESPACE" -o jsonpath='{.items[0].spec.containers[0].image}' 2>/dev/null || true
echo ""
echo ""
echo "Next steps:"
echo "  1. Apply Dapr components (pub/sub, state store):"
echo "     kubectl apply -f kafka-pubsub.yaml"
echo "     kubectl apply -f redis-statestore.yaml"
echo ""
echo "  2. Deploy your app with Dapr annotations enabled:"
echo "     helm upgrade --install backend ./backend/helm"
echo ""
echo "  3. Verify sidecar injection:"
echo "     kubectl get pods -o jsonpath='{.items[*].spec.containers[*].name}'"
echo "     (you should see 'daprd' alongside your app container)"
