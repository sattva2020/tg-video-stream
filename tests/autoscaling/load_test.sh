#!/bin/bash
# Load generation script for testing HPA (Horizontal Pod Autoscaler)
# Generates CPU load on backend, frontend, and transcoder services
#
# Usage:
#   ./load_test.sh [component] [duration] [concurrency]
#   component: backend | frontend | transcoder | all
#   duration: Load test duration in seconds (default: 60)
#   concurrency: Number of concurrent requests (default: 10)

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

# Generate load using a temporary pod
generate_load_with_pod() {
    local service_name=$1
    local service_port=$2
    local path=$3
    local duration=$4
    local concurrency=$5

    local job_name="load-gen-${service_name}-$(date +%s)"

    log_step "Generating load on $service_name for ${duration}s with $concurrency concurrent connections"

    cat <<EOF | kubectl apply -n "$NAMESPACE" -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $job_name
  namespace: $NAMESPACE
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      terminationGracePeriodSeconds: 5
      containers:
      - name: load-generator
        image: wrk/wrk:latest
        command: ["wrk"]
        args:
          - -t$concurrency
          - -c$concurrency
          - -d${duration}s
          - --timeout
          - "10s"
          - http://$RELEASE_NAME-$service_name:$service_port$path
EOF

    # Wait for job to complete
    log_info "Waiting for load generator job to complete..."
    if kubectl wait --for=condition=complete job "$job_name" -n "$NAMESPACE" --timeout=$((duration + 60))s 2>/dev/null; then
        log_info "Load generation completed successfully"

        # Get job logs
        local logs
        logs=$(kubectl logs "job/$job_name" -n "$NAMESPACE" --tail=20 2>/dev/null || echo "")
        if [ -n "$logs" ]; then
            log_info "Load test results:"
            echo "$logs" | sed 's/^/  /'
        fi

        # Cleanup job
        kubectl delete job "$job_name" -n "$NAMESPACE" --ignore-not-found=true &>/dev/null || true

        return 0
    else
        log_warn "Load generator job did not complete in time"
        kubectl delete job "$job_name" -n "$NAMESPACE" --ignore-not-found=true &>/dev/null || true
        return 1
    fi
}

# Generate load using Apache Bench (ab)
generate_load_with_ab() {
    local service_name=$1
    local service_port=$2
    local path=$3
    local duration=$4
    local concurrency=$5

    local pod_name="ab-load-gen-$(date +%s)"

    log_step "Generating load on $service_name using Apache Bench"

    cat <<EOF | kubectl apply -n "$NAMESPACE" -f -
apiVersion: v1
kind: Pod
metadata:
  name: $pod_name
  namespace: $NAMESPACE
spec:
  restartPolicy: Never
  containers:
  - name: ab
    image: citizenstig/ab:latest
    command: ["/bin/sh", "-c"]
    args:
      - |
        echo "Starting Apache Bench load test..."
        ab -n 100000 -c $concurrency -t $duration http://$RELEASE_NAME-$service_name:$service_port$path
        echo "Load test completed"
EOF

    # Wait for pod to be ready
    kubectl wait --for=condition=ready pod "$pod_name" -n "$NAMESPACE" --timeout=60s 2>/dev/null || true

    # Wait for test duration
    log_info "Running load test for ${duration}s..."
    sleep "$duration"

    # Get logs
    local logs
    logs=$(kubectl logs "$pod_name" -n "$NAMESPACE" --tail=50 2>/dev/null || echo "")

    if [ -n "$logs" ]; then
        log_info "Load test results:"
        echo "$logs" | sed 's/^/  /'
    fi

    # Cleanup pod
    kubectl delete pod "$pod_name" -n "$NAMESPACE" --ignore-not-found=true &>/dev/null || true
}

# Generate load using curl (simple method)
generate_load_with_curl() {
    local service_name=$1
    local service_port=$2
    local path=$3
    local duration=$4
    local concurrency=$5

    local pod_name="curl-load-gen-$(date +%s)"

    log_step "Generating load on $service_name using curl (simple method)"

    cat <<EOF | kubectl apply -n "$NAMESPACE" -f -
apiVersion: v1
kind: Pod
metadata:
  name: $pod_name
  namespace: $NAMESPACE
spec:
  restartPolicy: Never
  containers:
  - name: curl
    image: curlimages/curl:latest
    command: ["/bin/sh", "-c"]
    args:
      - |
        echo "Starting curl-based load generation..."
        end_time=\$(($(date +%s) + $duration))
        request_count=0

        while [ \$(date +%s) -lt \$end_time ]; do
          for i in \$(seq 1 $concurrency); do
            (curl -s -o /dev/null -w "%{http_code}\n" http://$RELEASE_NAME-$service_name:$service_port$path &) &
          done
          wait
          request_count=\$((request_count + concurrency))
          echo "Sent \$request_count requests..."
          sleep 1
        done

        echo "Load generation completed. Total requests: \$request_count"
EOF

    # Wait for pod to start
    kubectl wait --for=condition=Initialized pod "$pod_name" -n "$NAMESPACE" --timeout=30s 2>/dev/null || true

    # Monitor the test
    log_info "Running load test for ${duration}s..."
    sleep "$duration"

    # Get logs
    local logs
    logs=$(kubectl logs "$pod_name" -n "$NAMESPACE" --tail=20 2>/dev/null || echo "")

    if [ -n "$logs" ]; then
        log_info "Load test progress:"
        echo "$logs" | sed 's/^/  /'
    fi

    # Cleanup pod
    kubectl delete pod "$pod_name" -n "$NAMESPACE" --ignore-not-found=true &>/dev/null || true
}

# Generate CPU-intensive load
generate_cpu_load() {
    local service_name=$1
    local duration=${2:-60}

    local pod_name="cpu-stress-${service_name}-$(date +%s)"

    log_step "Generating CPU load on $service_name pods"

    # Find a pod for the service
    local target_pod
    target_pod=$(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/component=$service_name" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

    if [ -z "$target_pod" ]; then
        log_error "No pod found for $service_name"
        return 1
    fi

    log_info "Target pod: $target_pod"

    # Run stress command in the pod
    log_info "Running stress test for ${duration}s..."

    kubectl exec -n "$NAMESPACE" "$target_pod" -- sh -c "
        # Check if stress-ng is available
        if command -v stress-ng >/dev/null 2>&1; then
            stress-ng --cpu 2 --cpu-method all --timeout ${duration}s --metrics-brief
        # Check if stress is available
        elif command -v stress >/dev/null 2>&1; then
            stress --cpu 2 --timeout ${duration}s
        # Fallback: use a shell loop
        else
            echo 'Using shell loop for CPU stress...'
            end_time=\$(($(date +%s) + $duration))
            while [ \$(date +%s) -lt \$end_time ]; do
                : \$((\$RANDOM \% 1000 + 1))
            done
        fi
    " &

    local stress_pid=$!

    # Monitor the pod's CPU usage
    log_info "Monitoring pod CPU usage..."
    local elapsed=0
    local interval=10

    while [ $elapsed -lt $duration ]; do
        local cpu_usage
        cpu_usage=$(kubectl top pod "$target_pod" -n "$NAMESPACE" --no-headers 2>/dev/null | awk '{print $2}' || echo "N/A")

        log_info "[$elapsed s] $target_pod CPU: $cpu_usage"

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    # Wait for stress to complete
    wait $stress_pid 2>/dev/null || true

    log_info "CPU load generation completed"
}

# Generate mixed load (CPU + HTTP requests)
generate_mixed_load() {
    local service_name=$1
    local duration=${2:-60}
    local concurrency=${3:-10}

    log_step "Generating mixed load on $service_name"

    # Generate CPU load in background
    generate_cpu_load "$service_name" "$duration" &
    local cpu_pid=$!

    # Generate HTTP load
    local service_port
    local path

    case "$service_name" in
        backend)
            service_port=8000
            path="/api/health/ready"
            ;;
        frontend)
            service_port=80
            path="/"
            ;;
        rust-transcoder|transcoder)
            service_port=8090
            path="/health"
            ;;
        *)
            log_error "Unknown service: $service_name"
            return 1
            ;;
    esac

    generate_load_with_curl "$service_name" "$service_port" "$path" "$duration" "$concurrency"

    # Wait for CPU load to finish
    wait $cpu_pid 2>/dev/null || true

    log_info "Mixed load generation completed"
}

# Test backend load
test_backend_load() {
    local duration=${1:-60}
    local concurrency=${2:-10}

    log_info "Testing backend load"
    generate_mixed_load "backend" "$duration" "$concurrency"
}

# Test frontend load
test_frontend_load() {
    local duration=${1:-60}
    local concurrency=${2:-10}

    log_info "Testing frontend load"
    generate_mixed_load "frontend" "$duration" "$concurrency"
}

# Test transcoder load
test_transcoder_load() {
    local duration=${1:-60}
    local concurrency=${2:-10}

    log_info "Testing transcoder load"
    generate_mixed_load "rust-transcoder" "$duration" "$concurrency"
}

# Test all services
test_all_loads() {
    local duration=${1:-60}
    local concurrency=${2:-10}

    log_step "Testing load on all services"

    # Run load tests in parallel
    test_backend_load "$duration" "$concurrency" &
    local backend_pid=$!

    test_frontend_load "$duration" "$concurrency" &
    local frontend_pid=$!

    test_transcoder_load "$duration" "$concurrency" &
    local transcoder_pid=$!

    # Wait for all to complete
    log_info "Waiting for all load tests to complete..."
    wait $backend_pid $frontend_pid $transcoder_pid

    log_info "All load tests completed"
}

# Show usage
show_usage() {
    cat <<EOF
Load generation script for HPA testing

Usage: $0 [component] [duration] [concurrency]

Arguments:
  component     Service to test: backend, frontend, transcoder, or all (default: all)
  duration      Test duration in seconds (default: 60)
  concurrency   Number of concurrent connections (default: 10)

Examples:
  $0 backend 120 20              # Test backend for 120s with 20 concurrent connections
  $0 frontend 60 10              # Test frontend for 60s with 10 concurrent connections
  $0 all 120 30                  # Test all services for 120s with 30 concurrent connections

Environment variables:
  NAMESPACE       Kubernetes namespace (default: sattva-test)
  RELEASE_NAME    Helm release name (default: sattva-test)

Methods used (in order of preference):
  1. wrk - High-performance HTTP benchmarking tool
  2. Apache Bench (ab) - HTTP server benchmarking tool
  3. curl - Simple HTTP requests
  4. CPU stress - Direct CPU load on pods

EOF
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

    # Parse arguments
    local component="all"
    local duration=60
    local concurrency=10

    case "${1:-}" in
        backend)
            component="backend"
            ;;
        frontend)
            component="frontend"
            ;;
        transcoder|rust-transcoder)
            component="rust-transcoder"
            ;;
        all)
            component="all"
            ;;
        -h|--help|help)
            show_usage
            exit 0
            ;;
        "")
            component="all"
            ;;
        *)
            log_error "Unknown component: $1"
            show_usage
            exit 1
            ;;
    esac

    duration="${2:-60}"
    concurrency="${3:-10}"

    # Validate inputs
    if ! [[ "$duration" =~ ^[0-9]+$ ]] || [ "$duration" -lt 1 ]; then
        log_error "Invalid duration: $duration"
        exit 1
    fi

    if ! [[ "$concurrency" =~ ^[0-9]+$ ]] || [ "$concurrency" -lt 1 ]; then
        log_error "Invalid concurrency: $concurrency"
        exit 1
    fi

    # Run load test
    log_info "Starting load test..."
    log_info "Component: $component"
    log_info "Duration: ${duration}s"
    log_info "Concurrency: $concurrency"
    log_info "Namespace: $NAMESPACE"
    log_info "Release: $RELEASE_NAME"

    case "$component" in
        backend)
            test_backend_load "$duration" "$concurrency"
            ;;
        frontend)
            test_frontend_load "$duration" "$concurrency"
            ;;
        rust-transcoder)
            test_transcoder_load "$duration" "$concurrency"
            ;;
        all)
            test_all_loads "$duration" "$concurrency"
            ;;
    esac

    log_info "Load test completed successfully"
}

# Run main
main "$@"
