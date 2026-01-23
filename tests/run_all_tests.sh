#!/bin/bash
#
# run_all_tests.sh - Master test script for Kubernetes deployment
#
# Runs all test suites in order and generates comprehensive test report

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${1:-sattva-test}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_RESULTS_DIR="$PROJECT_ROOT/tests/test-results"
LOG_DIR="$PROJECT_ROOT/tests/logs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/test-run-$TIMESTAMP.log"

# Create directories
mkdir -p "$TEST_RESULTS_DIR"
mkdir -p "$LOG_DIR"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $*" | tee -a "$LOG_FILE"
}

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Run a test suite
run_test() {
    local test_name="$1"
    local test_command="$2"
    local critical="${3:-true}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log "Running: $test_name"

    if eval "$test_command" >> "$LOG_FILE" 2>&1; then
        log_success "$test_name PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "$test_name FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))

        if [[ "$critical" == "true" ]]; then
            log_error "Critical test failed, stopping execution"
            return 1
        fi
        return 0
    fi
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    local all_good=true

    # Check kubectl
    if command -v kubectl &> /dev/null; then
        log_success "kubectl installed: $(kubectl version --client --short 2>&1 | head -1)"
    else
        log_error "kubectl not found. Install from https://kubernetes.io/docs/tasks/tools/"
        all_good=false
    fi

    # Check cluster access
    if kubectl cluster-info &> /dev/null; then
        log_success "Cluster accessible: $(kubectl config current-context)"
    else
        log_error "Cannot access cluster. Run: kubectl config use-context <context>"
        all_good=false
    fi

    # Check Helm
    if command -v helm &> /dev/null; then
        log_success "Helm installed: $(helm version --short)"
    else
        log_error "Helm not found. Install from https://helm.sh/docs/intro/install/"
        all_good=false
    fi

    # Check helm unittest plugin
    if helm plugin list | grep -q unittest; then
        log_success "helm unittest plugin installed"
    else
        log_warning "helm unittest plugin not found. Installing..."
        helm plugin install https://github.com/quintush/helm-unittest >> "$LOG_FILE" 2>&1 || {
            log_error "Failed to install helm unittest plugin"
            all_good=false
        }
    fi

    # Check namespace
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE already exists"
    else
        log_success "Namespace $NAMESPACE will be created"
    fi

    if [[ "$all_good" == "false" ]]; then
        log_error "Prerequisites check failed"
        exit 1
    fi

    log_success "All prerequisites met"
}

# Test 1: Unit Tests
run_unit_tests() {
    print_header "Test Suite 1: Unit Tests (Helm Template Validation)"

    cd "$PROJECT_ROOT/helm/sattva-streamer"
    run_test "Helm Template Unit Tests" "helm unittest . --strict" "true"
    cd "$PROJECT_ROOT"
}

# Test 2: Integration Tests
run_integration_tests() {
    print_header "Test Suite 2: Integration Tests"

    if [[ -f "$PROJECT_ROOT/tests/helm/integration/deployment_test.sh" ]]; then
        run_test "Integration Tests" \
            "$PROJECT_ROOT/tests/helm/integration/deployment_test.sh $NAMESPACE" \
            "true"
    else
        log_warning "Integration test script not found, skipping"
    fi
}

# Test 3: E2E Tests
run_e2e_tests() {
    print_header "Test Suite 3: End-to-End Tests"

    if [[ -f "$PROJECT_ROOT/tests/e2e/k8s-deployment-e2e.test.sh" ]]; then
        run_test "E2E Deployment Tests" \
            "$PROJECT_ROOT/tests/e2e/k8s-deployment-e2e.test.sh $NAMESPACE" \
            "true"
    else
        log_warning "E2E test script not found, skipping"
    fi
}

# Test 4: Autoscaling Tests
run_autoscaling_tests() {
    print_header "Test Suite 4: Autoscaling Verification Tests"

    if [[ -f "$PROJECT_ROOT/tests/autoscaling/hpa_verification_test.sh" ]]; then
        run_test "HPA Verification Tests" \
            "$PROJECT_ROOT/tests/autoscaling/hpa_verification_test.sh $NAMESPACE" \
            "false"
    else
        log_warning "Autoscaling test script not found, skipping"
    fi
}

# Test 5: Disaster Recovery Tests
run_disaster_recovery_tests() {
    print_header "Test Suite 5: Disaster Recovery Tests"

    if [[ -f "$PROJECT_ROOT/tests/disaster-recovery/backup_restore_test.sh" ]]; then
        run_test "Backup/Restore Tests" \
            "$PROJECT_ROOT/tests/disaster-recovery/backup_restore_test.sh $NAMESPACE" \
            "false"
    else
        log_warning "Disaster recovery test script not found, skipping"
    fi
}

# Generate test report
generate_report() {
    print_header "Test Report"

    local report_file="$TEST_RESULTS_DIR/test-results-$TIMESTAMP.txt"

    cat > "$report_file" << EOF
========================================
Kubernetes Deployment Test Report
========================================
Run: $TIMESTAMP
Namespace: $NAMESPACE
Cluster: $(kubectl config current-context)

Summary:
--------
Total Tests: $TOTAL_TESTS
Passed: $PASSED_TESTS
Failed: $FAILED_TESTS
Success Rate: $(awk "BEGIN {printf \"%.1f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")%

Test Suites:
------------
EOF

    echo "Report generated: $report_file"
    cat "$report_file"

    # Copy latest
    cp "$report_file" "$TEST_RESULTS_DIR/latest.txt"

    # Final verdict
    echo ""
    if [[ $FAILED_TESTS -eq 0 ]]; then
        log_success "All tests PASSED! ✓"
        return 0
    else
        log_error "$FAILED_TESTS test(s) FAILED"
        return 1
    fi
}

# Cleanup on exit
cleanup() {
    local exit_code=$?

    print_header "Cleanup"

    log "Test logs saved to: $LOG_FILE"
    log "Test results saved to: $TEST_RESULTS_DIR/latest.txt"

    if [[ $exit_code -ne 0 ]]; then
        log_warning "Tests failed with exit code: $exit_code"
        log_warning "Namespace $NAMESPACE left for debugging"
        log_warning "To cleanup manually: kubectl delete namespace $NAMESPACE"
    fi

    exit $exit_code
}

trap cleanup EXIT

# Main execution
main() {
    print_header "Sattva Streamer K8s Test Suite"
    log "Starting tests at $(date)"
    log "Namespace: $NAMESPACE"
    log "Project root: $PROJECT_ROOT"

    check_prerequisites
    run_unit_tests
    run_integration_tests
    run_e2e_tests
    run_autoscaling_tests
    run_disaster_recovery_tests
    generate_report
}

# Run main function
main "$@"
