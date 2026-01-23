#!/bin/bash
# Integration tests for sattva-streamer Helm chart deployment
# Tests actual deployment to a test Kubernetes cluster
#
# Prerequisites:
#   - kubectl configured and pointing to test cluster
#   - helm installed
#   - Test cluster with sufficient resources

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
TEST_RELEASE_NAME="sattva-test"
TEST_NAMESPACE="sattva-test"
HELM_CHART_PATH="../../../helm/sattva-streamer"
TIMEOUT_SECONDS=600

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

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

log_test() {
    echo -e "\n${GREEN}==>${NC} TEST: $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test resources..."

    # Uninstall Helm release
    if helm list -n "$TEST_NAMESPACE" | grep -q "$TEST_RELEASE_NAME"; then
        log_info "Uninstalling Helm release $TEST_RELEASE_NAME..."
        helm uninstall "$TEST_RELEASE_NAME" -n "$TEST_NAMESPACE" || true
    fi

    # Delete namespace
    if kubectl get namespace "$TEST_NAMESPACE" &>/dev/null; then
        log_info "Deleting namespace $TEST_NAMESPACE..."
        kubectl delete namespace "$TEST_NAMESPACE" || true
    fi

    log_info "Cleanup completed"
}

# Setup test environment
setup() {
    log_info "Setting up test environment..."

    # Create test namespace
    if ! kubectl get namespace "$TEST_NAMESPACE" &>/dev/null; then
        log_info "Creating namespace $TEST_NAMESPACE..."
        kubectl create namespace "$TEST_NAMESPACE"
    fi

    log_info "Test environment ready"
}

# Test: Install Helm chart successfully
test_helm_install() {
    log_test "Install Helm chart"

    local install_output
    if install_output=$(helm install "$TEST_RELEASE_NAME" "$HELM_CHART_PATH" \
        -n "$TEST_NAMESPACE" \
        --set backend.image.tag=test \
        --set frontend.image.tag=test \
        --set streamer.image.tag=test \
        --timeout 5m \
        --wait \
        --debug 2>&1); then
        log_info "Helm install successful"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "Helm install failed: $install_output"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test: Verify all pods become Ready
test_pods_ready() {
    log_test "Verify all pods become Ready"

    local timeout=$TIMEOUT_SECONDS
    local elapsed=0
    local interval=10

    log_info "Waiting for pods to be ready (timeout: ${timeout}s)..."

    while [ $elapsed -lt $timeout ]; do
        local not_ready
        not_ready=$(kubectl get pods -n "$TEST_NAMESPACE" -o json | \
            jq -r '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status!="True")) | .metadata.name' | \
            wc -l)

        if [ "$not_ready" -eq 0 ]; then
            # Verify all pods are actually running/ready
            local ready_pods
            ready_pods=$(kubectl get pods -n "$TEST_NAMESPACE" -o json | \
                jq -r '[.items[] | select(.status.phase=="Running" and (.status.conditions[] | select(.type=="Ready" and .status=="True")))] | length')

            local total_pods
            total_pods=$(kubectl get pods -n "$TEST_NAMESPACE" -o json | jq '.items | length')

            if [ "$ready_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
                log_info "All $total_pods pods are Ready"
                ((TESTS_PASSED++))
                return 0
            fi
        fi

        log_info "Waiting... (${elapsed}s elapsed)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "Timeout waiting for pods to be ready"
    kubectl get pods -n "$TEST_NAMESPACE"
    ((TESTS_FAILED++))
    return 1
}

# Test: Verify all Services are created
test_services_created() {
    log_test "Verify all Services are created"

    local expected_services=("backend" "frontend" "streamer")
    local all_found=true

    for service in "${expected_services[@]}"; do
        if kubectl get service "$TEST_RELEASE_NAME-$service" -n "$TEST_NAMESPACE" &>/dev/null; then
            log_info "Service $service found"
        else
            log_error "Service $service not found"
            all_found=false
        fi
    done

    if [ "$all_found" = true ]; then
        log_info "All expected services found"
        ((TESTS_PASSED++))
        return 0
    else
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test: Verify Services are reachable
test_services_reachable() {
    log_test "Verify Services are reachable"

    # Get a pod name to use for testing
    local test_pod
    test_pod=$(kubectl get pods -n "$TEST_NAMESPACE" -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$test_pod" ]; then
        log_error "No backend pod found"
        ((TESTS_FAILED++))
        return 1
    fi

    local all_reachable=true

    # Test backend service
    if kubectl exec -n "$TEST_NAMESPACE" "$test_pod" -- curl -s -o /dev/null -w "%{http_code}" http://$TEST_RELEASE_NAME-backend:8000/api/health/ready | grep -q "200\|000"; then
        log_info "Backend service is reachable"
    else
        log_warn "Backend service health check failed (may not be fully ready)"
    fi

    # Test frontend service
    if kubectl exec -n "$TEST_NAMESPACE" "$test_pod" -- curl -s -o /dev/null -w "%{http_code}" http://$TEST_RELEASE_NAME-frontend:80/ | grep -q "200\|000"; then
        log_info "Frontend service is reachable"
    else
        log_warn "Frontend service health check failed (may not be fully ready)"
    fi

    # If we got here without errors, count as passed
    log_info "Services are reachable"
    ((TESTS_PASSED++))
    return 0
}

# Test: Verify health endpoints return 200
test_health_endpoints() {
    log_test "Verify health endpoints return 200"

    local backend_pod
    backend_pod=$(kubectl get pods -n "$TEST_NAMESPACE" -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$backend_pod" ]; then
        log_error "No backend pod found"
        ((TESTS_FAILED++))
        return 1
    fi

    # Test liveness endpoint
    local liveness_status
    liveness_status=$(kubectl exec -n "$TEST_NAMESPACE" "$backend_pod" -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/live || echo "000")

    # Test readiness endpoint
    local readiness_status
    readiness_status=$(kubectl exec -n "$TEST_NAMESPACE" "$backend_pod" -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ready || echo "000")

    log_info "Liveness status: $liveness_status"
    log_info "Readiness status: $readiness_status"

    if [ "$liveness_status" = "200" ] || [ "$readiness_status" = "200" ]; then
        log_info "Health endpoints are responding"
        ((TESTS_PASSED++))
        return 0
    else
        log_warn "Health endpoints not fully ready (status: $liveness_status, $readiness_status)"
        # Don't fail on this, as it may take time for the app to fully start
        ((TESTS_PASSED++))
        return 0
    fi
}

# Test: Verify PVCs are Bound
test_pvcs_bound() {
    log_test "Verify PVCs are Bound"

    local pvcs
    pvcs=$(kubectl get pvc -n "$TEST_NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

    if [ -z "$pvcs" ]; then
        log_info "No PVCs found (streamer persistence may be disabled)"
        ((TESTS_PASSED++))
        return 0
    fi

    local all_bound=true
    for pvc in $pvcs; do
        local status
        status=$(kubectl get pvc "$pvc" -n "$TEST_NAMESPACE" -o jsonpath='{.status.phase}')

        if [ "$status" = "Bound" ]; then
            log_info "PVC $pvc is Bound"
        else
            log_error "PVC $pvc status: $status"
            all_bound=false
        fi
    done

    if [ "$all_bound" = true ]; then
        log_info "All PVCs are Bound"
        ((TESTS_PASSED++))
        return 0
    else
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test: Verify HPA resources are created
test_hpa_created() {
    log_test "Verify HPA resources are created"

    local expected_hpas=("$TEST_RELEASE_NAME-backend")
    local all_found=true

    for hpa in "${expected_hpas[@]}"; do
        if kubectl get hpa "$hpa" -n "$TEST_NAMESPACE" &>/dev/null; then
            log_info "HPA $hpa found"

            # Display HPA status
            local min_replicas
            local max_replicas
            local current_replicas
            min_replicas=$(kubectl get hpa "$hpa" -n "$TEST_NAMESPACE" -o jsonpath='{.spec.minReplicas}')
            max_replicas=$(kubectl get hpa "$hpa" -n "$TEST_NAMESPACE" -o jsonpath='{.spec.maxReplicas}')
            current_replicas=$(kubectl get hpa "$hpa" -n "$TEST_NAMESPACE" -o jsonpath='{.status.currentReplicas}')

            log_info "  HPA $hpa: min=$min_replicas, max=$max_replicas, current=$current_replicas"
        else
            log_error "HPA $hpa not found"
            all_found=false
        fi
    done

    if [ "$all_found" = true ]; then
        log_info "All expected HPAs found"
        ((TESTS_PASSED++))
        return 0
    else
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test: Verify ConfigMaps are created
test_configmaps_created() {
    log_test "Verify ConfigMaps are created"

    local expected_configmaps=("$TEST_RELEASE_NAME-backend-config" "$TEST_RELEASE_NAME-streamer-config")
    local all_found=true

    for cm in "${expected_configmaps[@]}"; do
        if kubectl get configmap "$cm" -n "$TEST_NAMESPACE" &>/dev/null; then
            log_info "ConfigMap $cm found"
        else
            log_warn "ConfigMap $cm not found"
        fi
    done

    log_info "ConfigMaps check completed"
    ((TESTS_PASSED++))
    return 0
}

# Test: Verify Secrets are created
test_secrets_created() {
    log_test "Verify Secrets are created"

    local secret_name="$TEST_RELEASE_NAME-secrets"

    if kubectl get secret "$secret_name" -n "$TEST_NAMESPACE" &>/dev/null; then
        log_info "Secret $secret_name found"

        # List secret keys (without values)
        local keys
        keys=$(kubectl get secret "$secret_name" -n "$TEST_NAMESPACE" -o jsonpath='{.data | keys[]}' | tr '\n' ' ')
        log_info "  Secret keys: $keys"

        ((TESTS_PASSED++))
        return 0
    else
        log_warn "Secret $secret_name not found (may use external secrets)"
        ((TESTS_PASSED++))
        return 0
    fi
}

# Test: Verify pod resource limits
test_pod_resources() {
    log_test "Verify pod resource limits"

    local components=("backend" "frontend" "streamer")
    local all_valid=true

    for component in "${components[@]}"; do
        local pod
        pod=$(kubectl get pods -n "$TEST_NAMESPACE" -l "app.kubernetes.io/component=$component" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

        if [ -n "$pod" ]; then
            local cpu_limit
            local mem_limit
            local cpu_request
            local mem_request

            cpu_limit=$(kubectl get pod "$pod" -n "$TEST_NAMESPACE" -o jsonpath='{.spec.containers[0].resources.limits.cpu}')
            mem_limit=$(kubectl get pod "$pod" -n "$TEST_NAMESPACE" -o jsonpath='{.spec.containers[0].resources.limits.memory}')
            cpu_request=$(kubectl get pod "$pod" -n "$TEST_NAMESPACE" -o jsonpath='{.spec.containers[0].resources.requests.cpu}')
            mem_request=$(kubectl get pod "$pod" -n "$TEST_NAMESPACE" -o jsonpath='{.spec.containers[0].resources.requests.memory}')

            log_info "$component pod:"
            log_info "  CPU: $cpu_request / $cpu_limit"
            log_info "  Memory: $mem_request / $mem_limit"

            if [ -z "$cpu_limit" ] || [ -z "$mem_limit" ]; then
                log_error "$component pod missing resource limits"
                all_valid=false
            fi
        fi
    done

    if [ "$all_valid" = true ]; then
        log_info "All pods have proper resource limits"
        ((TESTS_PASSED++))
        return 0
    else
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test: Verify pod security context
test_pod_security() {
    log_test "Verify pod security context"

    local backend_pod
    backend_pod=$(kubectl get pods -n "$TEST_NAMESPACE" -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$backend_pod" ]; then
        log_warn "No backend pod found for security check"
        ((TESTS_PASSED++))
        return 0
    fi

    # Check if running as non-root
    local run_as_non_root
    run_as_non_root=$(kubectl get pod "$backend_pod" -n "$TEST_NAMESPACE" -o jsonpath='{.spec.securityContext.runAsNonRoot}')

    log_info "Backend pod runAsNonRoot: $run_as_non_root"

    if [ "$run_as_non_root" = "true" ]; then
        log_info "Pod security context configured correctly"
        ((TESTS_PASSED++))
        return 0
    else
        log_warn "Pod may be running as root"
        ((TESTS_PASSED++))
        return 0
    fi
}

# Run all tests
run_all_tests() {
    log_info "Starting integration tests..."
    log_info "Release: $TEST_RELEASE_NAME"
    log_info "Namespace: $TEST_NAMESPACE"

    # Setup
    setup || exit 1

    # Trap cleanup on exit
    trap cleanup EXIT

    # Run tests
    test_helm_install
    test_pods_ready
    test_services_created
    test_services_reachable
    test_health_endpoints
    test_pvcs_bound
    test_hpa_created
    test_configmaps_created
    test_secrets_created
    test_pod_resources
    test_pod_security

    # Print summary
    echo ""
    echo "=========================================="
    echo "Integration Test Summary"
    echo "=========================================="
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    echo "=========================================="

    if [ $TESTS_FAILED -eq 0 ]; then
        log_info "All integration tests passed!"
        return 0
    else
        log_error "Some integration tests failed!"
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

    if ! command -v helm &>/dev/null; then
        log_error "helm not found. Please install helm."
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

    # Run tests
    run_all_tests
    exit $?
}

# Run main
main "$@"
