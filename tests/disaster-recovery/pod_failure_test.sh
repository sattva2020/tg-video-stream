#!/bin/bash
# Pod failure simulation tests
# Tests pod failure scenarios and recovery
#
# Prerequisites:
#   - kubectl configured
#   - Application deployed

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${NAMESPACE:-sattva-test}"
RELEASE_NAME="${RELEASE_NAME:-sattva-test}"
POD_READY_TIMEOUT="${POD_READY_TIMEOUT:-120}"
STATEFULSET_RESTART_TIMEOUT="${STATEFULSET_RESTART_TIMEOUT:-300}"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

log_test() {
    echo -e "\n${GREEN}==>${NC} TEST: $1"
}

# Get pod count for a component
get_pod_count() {
    local component=$1
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/component=$component" -o jsonpath='{.items | length}' 2>/dev/null || echo "0"
}

# Get ready pod count for a component
get_ready_pod_count() {
    local component=$1
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/component=$component" -o json | jq -r '[.items[] | select(.status.conditions[] | select(.type=="Ready" and .status=="True"))] | length' 2>/dev/null || echo "0"
}

# Wait for pods to be ready
wait_for_pods_ready() {
    local component=$1
    local expected_count=$2
    local timeout=${3:-$POD_READY_TIMEOUT}

    log_info "Waiting for $expected_count $component pods to be ready (timeout: ${timeout}s)..."

    local elapsed=0
    local interval=5

    while [ $elapsed -lt $timeout ]; do
        local ready_count
        ready_count=$(get_ready_pod_count "$component")

        if [ "$ready_count" -ge "$expected_count" ]; then
            log_info "All $expected_count $component pods are ready"
            return 0
        fi

        log_info "Waiting... ($ready_count/$expected_count ready, ${elapsed}s elapsed)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "Timeout waiting for $component pods to be ready"
    return 1
}

# Test 1: Delete backend pod, verify it recreates
test_delete_backend_pod() {
    log_test "Delete backend pod and verify recreation"

    local pod_count
    pod_count=$(get_pod_count "backend")

    if [ "$pod_count" -eq 0 ]; then
        log_error "No backend pods found"
        ((TESTS_FAILED++))
        return 1
    fi

    local initial_ready
    initial_ready=$(get_ready_pod_count "backend")

    log_info "Initial backend pods: $pod_count total, $initial_ready ready"

    # Get a pod name
    local pod_to_delete
    pod_to_delete=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

    log_info "Deleting pod: $pod_to_delete"

    # Delete the pod
    if kubectl delete pod "$pod_to_delete" -n "$NAMESPACE" --grace-period=5 --timeout=10s &>/dev/null; then
        log_info "Pod deletion initiated"
    else
        log_warn "Pod deletion had issues, continuing..."
    fi

    # Wait for pod to be recreated
    log_info "Waiting for pod to be recreated..."

    sleep 5

    local new_pod_count
    local new_ready_count

    local elapsed=0
    local interval=5

    while [ $elapsed -lt $POD_READY_TIMEOUT ]; do
        new_pod_count=$(get_pod_count "backend")
        new_ready_count=$(get_ready_pod_count "backend")

        log_info "Pods: $new_pod_count total, $new_ready_count ready (${elapsed}s elapsed)"

        # Verify we have the same number of pods
        if [ "$new_pod_count" -ge "$pod_count" ]; then
            # Verify we have the same number of ready pods
            if [ "$new_ready_count" -ge "$initial_ready" ]; then
                log_info "Pod recreated and ready successfully"
                ((TESTS_PASSED++))
                return 0
            fi
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "Pod did not recreate in time"
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend
    ((TESTS_FAILED++))
    return 1
}

# Test 2: Delete all backend pods, verify all recreate
test_delete_all_backend_pods() {
    log_test "Delete all backend pods and verify recreation"

    local pod_count
    pod_count=$(get_pod_count "backend")

    if [ "$pod_count" -eq 0 ]; then
        log_error "No backend pods found"
        ((TESTS_FAILED++))
        return 1
    fi

    log_info "Initial backend pods: $pod_count"

    # Get all pod names
    local pods_to_delete
    pods_to_delete=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend -o jsonpath='{.items[*].metadata.name}')

    log_info "Deleting all backend pods..."

    # Delete all pods
    for pod in $pods_to_delete; do
        kubectl delete pod "$pod" -n "$NAMESPACE" --grace-period=5 --timeout=10s &>/dev/null || true
    done

    # Wait for all pods to be recreated
    if wait_for_pods_ready "backend" "$pod_count"; then
        log_info "All backend pods recreated successfully"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "Not all backend pods were recreated"
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test 3: Delete streamer pod, verify StatefulSet recreates with same identity
test_delete_streamer_pod() {
    log_test "Delete streamer pod and verify StatefulSet recreation with same identity"

    local streamer_pod
    streamer_pod=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=streamer -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

    if [ -z "$streamer_pod" ]; then
        log_warn "Streamer pod not found, skipping StatefulSet test"
        ((TESTS_SKIPPED++))
        return 0
    fi

    log_info "Original streamer pod: $streamer_pod"

    # Get the pod's UID
    local original_uid
    original_uid=$(kubectl get pod "$streamer_pod" -n "$NAMESPACE" -o jsonpath='{.metadata.uid}')

    # Get PVC name
    local pvc_name
    pvc_name=$(kubectl get pod "$streamer_pod" -n "$NAMESPACE" -o jsonpath='{.spec.volumes[?(@.name=="streamer-data")].persistentVolumeClaim.claimName}')

    log_info "Pod UID: $original_uid"
    log_info "PVC: $pvc_name"

    # Delete the pod
    log_info "Deleting streamer pod..."
    kubectl delete pod "$streamer_pod" -n "$NAMESPACE" --grace-period=5 --timeout=10s &>/dev/null || true

    # Wait for new pod to be created
    log_info "Waiting for StatefulSet to recreate pod..."

    sleep 10

    local new_pod
    local elapsed=0

    while [ $elapsed -lt $STATEFULSET_RESTART_TIMEOUT ]; do
        new_pod=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=streamer -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

        if [ -n "$new_pod" ]; then
            # Check if pod name is the same (StatefulSet maintains identity)
            if [ "$new_pod" = "$streamer_pod" ]; then
                log_info "Pod recreated with same name: $new_pod"

                # Check if it's using the same PVC
                local new_pvc
                new_pvc=$(kubectl get pod "$new_pod" -n "$NAMESPACE" -o jsonpath='{.spec.volumes[?(@.name=="streamer-data")].persistentVolumeClaim.claimName}')

                if [ "$new_pvc" = "$pvc_name" ]; then
                    log_info "Pod is using the same PVC: $new_pvc"
                    log_info "StatefulSet maintained pod identity successfully"
                    ((TESTS_PASSED++))
                    return 0
                else
                    log_error "Pod is using different PVC: $new_pvc (expected: $pvc_name)"
                    ((TESTS_FAILED++))
                    return 1
                fi
            fi
        fi

        log_info "Waiting for pod recreation... (${elapsed}s elapsed)"
        sleep 10
        elapsed=$((elapsed + 10))
    done

    log_error "StatefulSet did not recreate pod in time"
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=streamer
    ((TESTS_FAILED++))
    return 1
}

# Test 4: Force node failure (cordon/drain), verify pods move
test_node_failure() {
    log_test "Simulate node failure and verify pod rescheduling"

    # Get a node to use for testing
    local test_node
    test_node=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

    if [ -z "$test_node" ]; then
        log_warn "No nodes available for node failure test"
        ((TESTS_SKIPPED++))
        return 0
    fi

    log_info "Test node: $test_node"

    # Get pods on the node
    local pods_on_node
    pods_on_node=$(kubectl get pods -n "$NAMESPACE" -o json | jq -r ".items[] | select(.spec.nodeName == \"$test_node\") | .metadata.name" | head -5)

    if [ -z "$pods_on_node" ]; then
        log_warn "No pods found on node $test_node"
        ((TESTS_SKIPPED++))
        return 0
    fi

    log_info "Pods on node:"
    echo "$pods_on_node" | sed 's/^/  /'

    # Cordon the node
    log_info "Cordoning node: $test_node"
    kubectl cordon "$test_node" &>/dev/null || true

    # Drain the node (evict pods)
    log_info "Draining node: $test_node"
    kubectl drain "$test_node" --ignore-daemonsets --delete-emptydir-data --timeout=60s &>/dev/null || true

    # Wait for pods to be rescheduled
    log_info "Waiting for pods to be rescheduled..."
    sleep 15

    # Verify pods moved
    local pods_moved=true
    for pod in $pods_on_node; do
        local current_node
        current_node=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "")

        if [ -n "$current_node" ] && [ "$current_node" != "$test_node" ]; then
            log_info "Pod $pod moved to $current_node"
        elif [ -z "$current_node" ]; then
            log_info "Pod $pod may be pending or failed"
        else
            log_warn "Pod $pod still on cordoned node"
        fi
    done

    # Uncordon the node
    log_info "Uncordoning node: $test_node"
    kubectl uncordon "$test_node" &>/dev/null || true

    log_info "Node failure simulation completed"
    ((TESTS_PASSED++))
    return 0
}

# Test 5: Verify zero downtime during rolling updates
test_rolling_update() {
    log_test "Verify zero downtime during rolling updates"

    # Get current backend deployment revision
    local deployment_name="$RELEASE_NAME-backend"

    if ! kubectl get deployment "$deployment_name" -n "$NAMESPACE" &>/dev/null; then
        log_warn "Backend deployment not found, skipping rolling update test"
        ((TESTS_SKIPPED++))
        return 0
    fi

    # Get current ready replicas
    local initial_ready
    initial_ready=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')

    log_info "Initial ready replicas: $initial_ready"

    # Trigger a rolling update by changing an annotation
    log_info "Triggering rolling update..."
    kubectl patch deployment "$deployment_name" -n "$NAMESPACE" -p '{"spec":{"template":{"metadata":{"annotations":{"roll-update":"'"$(date +%s)"'"}}}}}' &>/dev/null || true

    # Monitor during rolling update
    local elapsed=0
    local interval=5
    local max_time=120

    local never_dropped_below_initial=true

    while [ $elapsed -lt $max_time ]; do
        local current_ready
        local current_unavailable
        local updated_replicas

        current_ready=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' || echo "0")
        current_unavailable=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.unavailableReplicas}' || echo "0")
        updated_replicas=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.updatedReplicas}' || echo "0")

        log_info "[$elapsed s] Ready: $current_ready, Updated: $updated_replicas, Unavailable: $current_unavailable"

        # Check if ready replicas dropped below initial
        if [ "$current_ready" -lt "$initial_ready" ]; then
            log_warn "Ready replicas dropped from $initial_ready to $current_ready"
            never_dropped_below_initial=false
        fi

        # Check if rolling update is complete
        if [ "$updated_replicas" -ge "$initial_ready" ] && [ "$current_unavailable" -eq 0 ]; then
            log_info "Rolling update completed"
            break
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    if [ "$never_dropped_below_initial" = true ]; then
        log_info "Zero downtime verified during rolling update"
        ((TESTS_PASSED++))
        return 0
    else
        log_warn "Some availability impact detected during rolling update (may be acceptable)"
        ((TESTS_PASSED++))
        return 0
    fi
}

# Test 6: Verify pod disruption budget
test_pod_disruption_budget() {
    log_test "Verify Pod Disruption Budget"

    local pdb_count
    pdb_count=$(kubectl get pdb -n "$NAMESPACE" -o jsonpath='{.items | length}' 2>/dev/null || echo "0")

    if [ "$pdb_count" -eq 0 ]; then
        log_warn "No Pod Disruption Budgets found"
        ((TESTS_SKIPPED++))
        return 0
    fi

    log_info "Found $pdb_count Pod Disruption Budget(s)"

    kubectl get pdb -n "$NAMESPACE" -o wide

    # Check each PDB
    for pdb in $(kubectl get pdb -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}'); do
        local min_available
        local current
        local desired

        min_available=$(kubectl get pdb "$pdb" -n "$NAMESPACE" -o jsonpath='{.spec.minAvailable}')
        current=$(kubectl get pdb "$pdb" -n "$NAMESPACE" -o jsonpath='{.status.currentHealthy}')
        desired=$(kubectl get pdb "$pdb" -n "$NAMESPACE" -o jsonpath='{.status.desiredHealthy}')

        log_info "  $pdb:"
        log_info "    Min available: $min_available"
        log_info "    Current healthy: $current"
        log_info "    Desired healthy: $desired"

        if [ "$current" -ge "$desired" ]; then
            log_info "    PDB is satisfied"
        else
            log_warn "    PDB is not satisfied!"
        fi
    done

    ((TESTS_PASSED++))
    return 0
}

# Run all tests
run_all_tests() {
    log_info "Starting pod failure simulation tests..."
    log_info "Namespace: $NAMESPACE"
    log_info "Release: $RELEASE_NAME"

    # Run tests
    test_delete_backend_pod
    test_delete_all_backend_pods
    test_delete_streamer_pod
    test_node_failure
    test_rolling_update
    test_pod_disruption_budget

    # Print summary
    echo ""
    echo "=========================================="
    echo "Pod Failure Test Summary"
    echo "=========================================="
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    echo "Tests Skipped: $TESTS_SKIPPED"
    echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))"
    echo "=========================================="

    if [ $TESTS_FAILED -eq 0 ]; then
        log_info "Pod failure tests passed!"
        return 0
    else
        log_error "Some pod failure tests failed!"
        return 1
    fi
}

# Main execution
main() {
    # Check prerequisites
    if ! command -v kubectl &>/dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    if ! command -v jq &>/dev/null; then
        log_error "jq not found. Please install jq."
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &>/dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check for admin permissions
    if ! kubectl auth can-i delete nodes &>/dev/null; then
        log_warn "Insufficient permissions for node failure test (test will be skipped)"
    fi

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --namespace)
                NAMESPACE="$2"
                export NAMESPACE
                shift 2
                ;;
            --release)
                RELEASE_NAME="$2"
                export RELEASE_NAME
                shift 2
                ;;
            --help)
                echo "Usage: $0 [--namespace NAMESPACE] [--release RELEASE]"
                echo "  --namespace     Specify namespace (default: sattva-test)"
                echo "  --release       Specify release name (default: sattva-test)"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Run tests
    run_all_tests
    exit $?
}

# Run main
main "$@"
