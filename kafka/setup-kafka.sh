#!/bin/bash
# Kafka Setup Script for Tasks API (using Strimzi Operator)
#
# Strimzi is a Kubernetes operator for Apache Kafka. Unlike a plain Helm chart
# that just creates pods, Strimzi uses the "operator pattern":
#   1. You install the Strimzi operator (a controller that watches for Kafka CRDs)
#   2. You create a Kafka Custom Resource (CR) describing your desired cluster
#   3. The operator sees the CR and creates/manages all the Kafka pods for you
#
# This means upgrades, scaling, and configuration changes are handled
# automatically by the operator — you just update the CR.
#
# Usage:
#   Development: ./setup-kafka.sh dev
#   Production:  ./setup-kafka.sh prod
#
# Prerequisites:
#   - kubectl configured with cluster access
#   - helm installed

set -e

MODE="${1:-dev}"
KAFKA_NAMESPACE="${KAFKA_NAMESPACE:-kafka}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Kafka Setup for Tasks API (Strimzi) ==="
echo "Mode: $MODE"
echo "Namespace: $KAFKA_NAMESPACE"
echo ""

# Add Strimzi Helm repo
echo "Adding Strimzi Helm repository..."
helm repo add strimzi https://strimzi.io/charts/ 2>/dev/null || true
helm repo update

# Create namespace
kubectl create namespace "$KAFKA_NAMESPACE" 2>/dev/null || true

# Step 1: Install the Strimzi operator
# This installs the operator itself — it doesn't create any Kafka clusters yet.
# The operator watches for Kafka CRDs and manages the lifecycle of Kafka clusters.
if [ "$MODE" = "dev" ]; then
    echo "Installing Strimzi operator in DEVELOPMENT mode..."
    helm upgrade --install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
        -f "$SCRIPT_DIR/kafka-helm-values-dev.yaml" \
        -n "$KAFKA_NAMESPACE" \
        --wait --timeout 3m
else
    echo "Installing Strimzi operator in PRODUCTION mode..."
    helm upgrade --install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
        -f "$SCRIPT_DIR/kafka-helm-values-prod.yaml" \
        -n "$KAFKA_NAMESPACE" \
        --wait --timeout 3m
fi

# Wait for operator to be ready
echo "Waiting for Strimzi operator to be ready..."
kubectl wait --for=condition=Ready pod -l name=strimzi-cluster-operator \
    -n "$KAFKA_NAMESPACE" --timeout=120s

# Step 2: Create the Kafka cluster
# Now we apply the Kafka CR — the operator will see this and create the
# actual Kafka broker pods, ZooKeeper pods, and entity operator.
echo ""
echo "Creating Kafka cluster..."
if [ "$MODE" = "dev" ]; then
    kubectl apply -f "$SCRIPT_DIR/kafka-cluster-dev.yaml"
else
    kubectl apply -f "$SCRIPT_DIR/kafka-cluster-prod.yaml"
fi

# Wait for Kafka cluster to be ready
# The operator creates pods in stages: ZooKeeper first, then Kafka brokers
echo "Waiting for Kafka cluster to be ready (this may take 2-3 minutes)..."
kubectl wait kafka/kafka --for=condition=Ready \
    -n "$KAFKA_NAMESPACE" --timeout=300s

echo ""
echo "=== Kafka Setup Complete ==="
echo ""
echo "Kafka pods:"
kubectl get pods -n "$KAFKA_NAMESPACE"
echo ""
echo "Kafka broker address (use this in Dapr component):"
echo "  kafka-kafka-bootstrap.$KAFKA_NAMESPACE.svc.cluster.local:9092"
echo ""
echo "To test Kafka manually:"
echo "  # Start a producer:"
echo "  kubectl run kafka-producer -it --rm --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 -- \\"
echo "    bin/kafka-console-producer.sh --bootstrap-server kafka-kafka-bootstrap.$KAFKA_NAMESPACE.svc.cluster.local:9092 --topic test"
echo ""
echo "  # In another terminal, start a consumer:"
echo "  kubectl run kafka-consumer -it --rm --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 -- \\"
echo "    bin/kafka-console-consumer.sh --bootstrap-server kafka-kafka-bootstrap.$KAFKA_NAMESPACE.svc.cluster.local:9092 --topic test --from-beginning"
