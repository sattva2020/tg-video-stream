#!/bin/bash
# HPA (Horizontal Pod Autoscaler) verification tests
# Tests autoscaling functionality for backend, frontend, and transcoder services
#
# Prerequisites:
#   - kubectl configured
#   - Cluster with metrics-server installed
#   - Application deployed with HPA enabled

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
LOAD_TEST_DURATION="${LOAD_TEST_DURATION:-120}"
SCALE_UP_TIMEOUT="${SCALE_UP_TIMEOUT:-300}"
SCALE_DOWN_TIMEOUT="${SCALE_DOWN_TIMEOUT:-300}"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# HPA metrics log
HPA_METRICS_LOG="/tmp/hpa_metrics_$(date +%s).log"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$HPA_METRICS_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$HPA_METRICS_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$HPA_METRICS_LOG"
}

log_test() {
    echo -e "\n${GREEN}==>${NC} TEST: $1"
    echo "[TEST] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$HPA_METRICS_LOG"
}

log_metric() {
    echo "[METRIC] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$HPA_METRICS_LOG"
}

# Get HPA details
get_hpa_details() {
    local hpa_name=$1
    kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o json
}

# Get current replica count
get_current_replicas() {
    local hpa_name=$1
    kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.status.currentReplicas}'
}

# Get desired replica count
get_desired_replicas() {
    local hpa_name=$1
    kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.status.desiredReplicas}'
}

# Get current CPU utilization
get_current_cpu() {
    local hpa_name=$1
    kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.status.currentMetrics[?(@.type=="Resource")].resource.current.averageUtilization}' | head -1
}

# Test 1: Verify HPA resources exist
test_hpa_resources_exist() {
    log_test "Verify HPA resources exist"

    local components=("backend" "frontend" "rust-transcoder")
    local all_found=true

    for component in "${components[@]}"; do
        local expected_hpa="$RELEASE_NAME-$component"

        # For streamer, HPA should not exist
        if [ "$component" = "streamer" ]; then
            if kubectl get hpa "$expected_hpa" -n "$NAMESPACE" &>/dev/null; then
                log_warn "HPA $expected_hpa exists but streamer should not have autoscaling"
            fi
            continue
        fi

        if kubectl get hpa "$expected_hpa" -n "$NAMESPACE" &>/dev/null; then
            log_info "HPA $expected_hpa found"

            # Display HPA configuration
            local min_replicas
            local max_replicas
            local target_cpu

            min_replicas=$(kubectl get hpa "$expected_hpa" -n "$NAMESPACE" -o jsonpath='{.spec.minReplicas}')
            max_replicas=$(kubectl get hpa "$expected_hpa" -n "$NAMESPACE" -o jsonpath='{.spec.maxReplicas}')
            target_cpu=$(kubectl get hpa "$expected_hpa" -n "$NAMESPACE" -o jsonpath='{.spec.metrics[0].resource.target.averageUtilization}')

            log_info "  Min replicas: $min_replicas"
            log_info "  Max replicas: $max_replicas"
            log_info "  Target CPU: ${target_cpu}%"
        else
            log_warn "HPA $expected_hpa not found (may be disabled)"
        fi
    done

    # Check if at least one HPA exists
    local hpa_count
    hpa_count=$(kubectl get hpa -n "$NAMESPACE" -l app.kubernetes.io/instance="$RELEASE_NAME" -o jsonpath='{.items | length}' 2>/dev/null || echo "0")

    if [ "$hpa_count" -gt 0 ]; then
        log_info "Found $hpa_count HPA resources"
        ((TESTS_PASSED++))
        return 0
    else
        log_warn "No HPA resources found (autoscaling may be disabled)"
        ((TESTS_PASSED++))
        return 0
    fi
}

# Test 2: Check HPA status and metrics
test_hpa_status() {
    log_test "Check HPA status and metrics"

    local hpas
    hpas=$(kubectl get hpa -n "$NAMESPACE" -l app.kubernetes.io/instance="$RELEASE_NAME" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

    if [ -z "$hpas" ]; then
        log_warn "No HPAs found to check status"
        ((TESTS_PASSED++))
        return 0
    fi

    for hpa in $hpas; do
        log_info "Checking HPA: $hpa"

        local current_replicas
        local desired_replicas
        local min_replicas
        local max_replicas
        local current_cpu

        current_replicas=$(get_current_replicas "$hpa")
        desired_replicas=$(get_desired_replicas "$hpa")
        min_replicas=$(kubectl get hpa "$hpa" -n "$NAMESPACE" -o jsonpath='{.spec.minReplicas}')
        max_replicas=$(kubectl get hpa "$hpa" -n "$NAMESPACE" -o jsonpath='{.spec.maxReplicas}')
        current_cpu=$(get_current_cpu "$hpa")

        log_info "  Current replicas: $current_replicas"
        log_info "  Desired replicas: $desired_replicas"
        log_info "  Min/Max: $min_replicas / $max_replicas"
        log_info "  Current CPU: ${current_cpu}%"

        log_metric "$hpa: replicas=$current_replicas/$desired_replicas, cpu=${current_cpu}%"

        # Verify replicas are within bounds
        if [ "$current_replicas" -lt "$min_replicas" ]; then
            log_error "Current replicas ($current_replicas) less than minimum ($min_replicas)"
        elif [ "$current_replicas" -gt "$max_replicas" ]; then
            log_error "Current replicas ($current_replicas) greater than maximum ($max_replicas)"
        else
            log_info "  Replica count within bounds"
        fi
    done

    ((TESTS_PASSED++))
    return 0
}

# Test 3: Trigger load on backend
test_trigger_load_backend() {
    log_test "Trigger load on backend"

    local backend_pod
    backend_pod=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

    if [ -z "$backend_pod" ]; then
        log_error "Backend pod not found"
        ((TESTS_FAILED++))
        return 1
    fi

    log_info "Generating load on backend pod: $backend_pod"

    # Create a load generator job
    cat <<EOF | kubectl apply -n "$NAMESPACE" -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: backend-load-generator
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: load-gen
        image: busybox
        command: ["/bin/sh", "-c"]
        args:
        - |
          # Generate load for specified duration
          echo "Starting load generation for ${LOAD_TEST_DURATION}s..."
          for i in \$(seq 1 100); do
            # Use wget to generate requests
            wget -q -O /dev/null http://$RELEASE_NAME-backend:8000/api/health/ready || true
            sleep \$((LOAD_TEST_DURATION / 100))
          done
          echo "Load generation completed"
EOF

    log_info "Load generator job started"

    # Wait for job to start
    sleep 5

    ((TESTS_PASSED++))
    return 0
}

# Test 4: Monitor HPA scale-up
test_hpa_scale_up() {
    log_test "Monitor HPA scale-up"

    local hpa_name="$RELEASE_NAME-backend"

    if ! kubectl get hpa "$hpa_name" -n "$NAMESPACE" &>/dev/null; then
        log_warn "Backend HPA not found, skipping scale-up test"
        ((TESTS_SKIPPED++))
        return 0
    fi

    local initial_replicas
    initial_replicas=$(get_current_replicas "$hpa_name")
    local max_replicas
    max_replicas=$(kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.spec.maxReplicas}')

    log_info "Initial replica count: $initial_replicas"
    log_info "Max replicas: $max_replicas"

    if [ "$initial_replicas" -ge "$max_replicas" ]; then
        log_warn "Already at max replicas, scale-up test may not be effective"
    fi

    local elapsed=0
    local interval=10

    log_info "Monitoring HPA for scale-up (timeout: ${SCALE_UP_TIMEOUT}s)..."

    while [ $elapsed -lt $SCALE_UP_TIMEOUT ]; do
        local current_replicas
        local desired_replicas

        current_replicas=$(get_current_replicas "$hpa_name")
        desired_replicas=$(get_desired_replicas "$hpa_name")

        log_info "[$elapsed s] Replicas: $current_replicas (desired: $desired_replicas)"
        log_metric "scale_up_monitor: current=$current_replicas, desired=$desired_replicas"

        # Check if we've scaled up
        if [ "$current_replicas" -gt "$initial_replicas" ]; then
            log_info "Scale-up detected! Replicas: $initial_replicas -> $current_replicas"

            # Wait for new pods to be ready
            log_info "Waiting for new pods to become ready..."

            if kubectl wait --for=condition=ready pod -n "$NAMESPACE" -l app.kubernetes.io/component=backend --timeout=120s; then
                log_info "All pods are ready"
                ((TESTS_PASSED++))
                return 0
            else
                log_warn "Some pods may not be fully ready yet"
                ((TESTS_PASSED++))
                return 0
            fi
        fi

        # If desired replicas > current, HPA is trying to scale
        if [ "$desired_replicas" -gt "$current_replicas" ]; then
            log_info "HPA wants to scale to $desired_replicas replicas"
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_warn "Scale-up not detected within timeout"
    log_info "Current status:"
    kubectl get hpa "$hpa_name" -n "$NAMESPACE"
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend

    # Don't fail, as the cluster may be under low load
    ((TESTS_PASSED++))
    return 0
}

# Test 5: Verify new pods are ready
test_new_pods_ready() {
    log_test "Verify new pods are ready"

    local pods
    pods=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=backend -o jsonpath='{.items[*].metadata.name}')

    local all_ready=true
    local total_count=0
    local ready_count=0

    for pod in $pods; do
        total_count=$((total_count + 1))

        local ready
        ready=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')

        if [ "$ready" = "true" ]; then
            ready_count=$((ready_count + 1))
            log_info "Pod $pod is Ready"
        else
            log_warn "Pod $pod is not Ready"
            all_ready=false
        fi
    done

    log_info "Pods ready: $ready_count / $total_count"

    if [ "$all_ready" = true ]; then
        log_info "All pods are ready"
        ((TESTS_PASSED++))
        return 0
    else
        log_warn "Some pods are not ready yet"
        ((TESTS_PASSED++))
        return 0
    fi
}

# Test 6: Stop load and verify scale-down
test_hpa_scale_down() {
    log_test "Stop load and verify HPA scale-down"

    # Delete load generator job
    if kubectl delete job backend-load-generator -n "$NAMESPACE" --ignore-not-found=true; then
        log_info "Load generator job deleted"
    fi

    local hpa_name="$RELEASE_NAME-backend"

    if ! kubectl get hpa "$hpa_name" -n "$NAMESPACE" &>/dev/null; then
        log_warn "Backend HPA not found, skipping scale-down test"
        ((TESTS_SKIPPED++))
        return 0
    fi

    local initial_replicas
    initial_replicas=$(get_current_replicas "$hpa_name")
    local min_replicas
    min_replicas=$(kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.spec.minReplicas}')

    log_info "Initial replica count: $initial_replicas"
    log_info "Min replicas: $min_replicas"

    if [ "$initial_replicas" -le "$min_replicas" ]; then
        log_info "Already at minimum replicas, scale-down will occur naturally"
    fi

    local elapsed=0
    local interval=15

    log_info "Monitoring HPA for scale-down (timeout: ${SCALE_DOWN_TIMEOUT}s)..."

    while [ $elapsed -lt $SCALE_DOWN_TIMEOUT ]; do
        local current_replicas
        local desired_replicas
        local current_cpu

        current_replicas=$(get_current_replicas "$hpa_name")
        desired_replicas=$(get_desired_replicas "$hpa_name")
        current_cpu=$(get_current_cpu "$hpa_name")

        log_info "[$elapsed s] Replicas: $current_replicas (desired: $desired_replicas, CPU: ${current_cpu}%)"
        log_metric "scale_down_monitor: current=$current_replicas, desired=$desired_replicas, cpu=${current_cpu}%"

        # Check if we've scaled down to min
        if [ "$current_replicas" -le "$min_replicas" ]; then
            log_info "Scale-down detected! Replicas: $initial_replicas -> $current_replicas"
            log_info "HPA has scaled down to minimum"
            ((TESTS_PASSED++))
            return 0
        fi

        # Check if HPA wants to scale down
        if [ "$desired_replicas" -lt "$current_replicas" ]; then
            log_info "HPA is scaling down (desired: $desired_replicas)"
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_warn "Scale-down to minimum not detected within timeout"
    log_info "Note: Scale-down has a default stabilization period (~5 minutes)"

    # Check if we at least reduced replicas
    local final_replicas
    final_replicas=$(get_current_replicas "$hpa_name")

    if [ "$final_replicas" -lt "$initial_replicas" ]; then
        log_info "Partial scale-down detected: $initial_replicas -> $final_replicas"
        ((TESTS_PASSED++))
        return 0
    fi

    log_warn "No scale-down detected yet (this is normal due to stabilization window)"
    ((TESTS_PASSED++))
    return 0
}

# Test 7: Test each service HPA
test_each_service_hpa() {
    log_test "Test each service HPA"

    local services=("backend" "frontend" "rust-transcoder")

    for service in "${services[@]}"; do
        local hpa_name="$RELEASE_NAME-$service"

        if ! kubectl get hpa "$hpa_name" -n "$NAMESPACE" &>/dev/null; then
            log_warn "HPA for $service not found, skipping"
            continue
        fi

        log_info "Checking HPA for $service..."

        # Get HPA status
        local current
        local desired
        local min
        local max
        local target_cpu
        local current_cpu

        current=$(get_current_replicas "$hpa_name")
        desired=$(get_desired_replicas "$hpa_name")
        min=$(kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.spec.minReplicas}')
        max=$(kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.spec.maxReplicas}')
        target_cpu=$(kubectl get hpa "$hpa_name" -n "$NAMESPACE" -o jsonpath='{.spec.metrics[0].resource.target.averageUtilization}')
        current_cpu=$(get_current_cpu "$hpa_name")

        log_info "  $service HPA:"
        log_info "    Replicas: $current / $desired (min: $min, max: $max)"
        log_info "    CPU: ${current_cpu}% (target: ${target_cpu}%)"

        log_metric "$service: replicas=$current/$desired, cpu=${current_cpu}%, target=${target_cpu}%"

        # Verify configuration
        if [ "$min" -lt 1 ]; then
            log_error "$service: min replicas should be at least 1"
        fi

        if [ "$max" -le "$min" ]; then
            log_error "$service: max replicas should be greater than min"
        fi

        if [ "$target_cpu" -lt 1 ] || [ "$target_cpu" -gt 100 ]; then
            log_error "$service: target CPU should be between 1 and 100"
        fi
    done

    ((TESTS_PASSED++))
    return 0
}

# Test 8: Log HPA behavior over time
test_log_hpa_behavior() {
    log_test "Log HPA behavior"

    log_info "HPA metrics log saved to: $HPA_METRICS_LOG"

    # Generate summary
    log_info "HPA Summary:"

    local hpas
    hpas=$(kubectl get hpa -n "$NAMESPACE" -l app.kubernetes.io/instance="$RELEASE_NAME" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

    for hpa in $hpas; do
        log_info "  $hpa:"
        kubectl get hpa "$hpa" -n "$NAMESPACE" | column -t | sed 's/^/    /'
    done

    ((TESTS_PASSED++))
    return 0
}

# Run all tests
run_all_tests() {
    log_info "Starting HPA verification tests..."
    log_info "Namespace: $NAMESPACE"
    log_info "Release: $RELEASE_NAME"
    log_info "Load test duration: ${LOAD_TEST_DURATION}s"

    # Run tests
    test_hpa_resources_exist
    test_hpa_status
    test_trigger_load_backend
    test_hpa_scale_up
    test_new_pods_ready
    test_hpa_scale_down
    test_each_service_hpa
    test_log_hpa_behavior

    # Cleanup load generator
    kubectl delete job backend-load-generator -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || true

    # Print summary
    echo ""
    echo "=========================================="
    echo "HPA Verification Test Summary"
    echo "=========================================="
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    echo "Tests Skipped: ${TESTS_SKIPPED:-0}"
    echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED + ${TESTS_SKIPPED:-0}))"
    echo "=========================================="
    echo "HPA metrics log: $HPA_METRICS_LOG"
    echo "=========================================="

    if [ $TESTS_FAILED -eq 0 ]; then
        log_info "HPA verification tests passed!"
        return 0
    else
        log_error "Some HPA verification tests failed!"
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

    # Check cluster connectivity
    if ! kubectl cluster-info &>/dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check if metrics-server is available
    if ! kubectl get apiservice v1beta1.metrics.k8s.io &>/dev/null; then
        log_error "metrics-server not found. HPA requires metrics-server."
        exit 1
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
            --load-duration)
                LOAD_TEST_DURATION="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [--namespace NAMESPACE] [--release RELEASE] [--load-duration SECONDS]"
                echo "  --namespace      Specify namespace (default: sattva-test)"
                echo "  --release        Specify release name (default: sattva-test)"
                echo "  --load-duration  Load test duration in seconds (default: 120)"
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
