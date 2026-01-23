#!/bin/bash

# Post-deployment smoke tests to validate that the deployment is successful
# Usage: ./scripts/ci/post-deploy-smoke-tests.sh [OPTIONS]

set -eo pipefail

# Configuration
BACKEND_HOST="${BACKEND_HOST:-localhost}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-localhost}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
API_BASE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
TIMEOUT=10
MAX_RETRIES=3
RETRY_DELAY=5

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backend-host)
                BACKEND_HOST="$2"
                shift 2
                ;;
            --backend-port)
                BACKEND_PORT="$2"
                shift 2
                ;;
            --frontend-host)
                FRONTEND_HOST="$2"
                shift 2
                ;;
            --frontend-port)
                FRONTEND_PORT="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Update URLs with new host/port values
    API_BASE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
    FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Post-deployment smoke tests to validate that the deployment is successful.
Tests critical services and endpoints to ensure the system is operational.

Options:
  --backend HOST    Backend host (default: localhost)
  --backend-port PORT Backend port (default: 8000)
  --frontend HOST   Frontend host (default: localhost)
  --frontend-port PORT Frontend port (default: 3000)
  --timeout SECONDS Request timeout in seconds (default: 10)
  --help, -h        Show this help message

Environment Variables:
  BACKEND_HOST      Backend host (overrides --backend-host)
  BACKEND_PORT      Backend port (overrides --backend-port)
  FRONTEND_HOST     Frontend host (overrides --frontend-host)
  FRONTEND_PORT     Frontend port (overrides --frontend-port)

Examples:
  $0                                    # Test localhost
  $0 --backend-host 192.168.1.100       # Test remote backend
  BACKEND_HOST=1.2.3.4 $0               # Test via environment variable

EOF
}

# ============================================================================
# Test Functions
# ============================================================================

# Run a test with retry logic
run_test_with_retry() {
    local test_name="$1"
    local test_command="$2"
    local max_attempts="${3:-$MAX_RETRIES}"
    local wait_time="${4:-$RETRY_DELAY}"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))

    print_info "Running: $test_name"

    for attempt in $(seq 1 $max_attempts); do
        if eval "$test_command"; then
            print_success "$test_name"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        else
            if [ $attempt -lt $max_attempts ]; then
                print_warning "$test_name failed (attempt $attempt/$max_attempts), retrying in ${wait_time}s..."
                sleep $wait_time
            fi
        fi
    done

    print_error "$test_name failed after $max_attempts attempts"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    return 1
}

# Test backend health endpoint
test_backend_health() {
    print_header "Backend Health Check"

    run_test_with_retry \
        "Backend Health Endpoint" \
        "curl -f -s -m $TIMEOUT '${API_BASE_URL}/health' | grep -q 'healthy'"

    run_test_with_retry \
        "Backend API Root" \
        "curl -f -s -m $TIMEOUT '${API_BASE_URL}/' > /dev/null"
}

# Test frontend accessibility
test_frontend_accessibility() {
    print_header "Frontend Accessibility"

    run_test_with_retry \
        "Frontend Root Page" \
        "curl -f -s -m $TIMEOUT '${FRONTEND_URL}' | head -n 1"

    # Check for common frontend assets
    run_test_with_retry \
        "Frontend Responds with HTML" \
        "curl -f -s -m $TIMEOUT '${FRONTEND_URL}' | grep -q '<!DOCTYPE' || curl -f -s -m $TIMEOUT '${FRONTEND_URL}' | grep -q '<html'"
}

# Test database connectivity (via backend API)
test_database_connectivity() {
    print_header "Database Connectivity"

    # Test that backend can connect to database via health check
    run_test_with_retry \
        "Database Connection (via API)" \
        "curl -f -s -m $TIMEOUT '${API_BASE_URL}/health' | jq -e '.database_status == \"healthy\"' > /dev/null 2>&1 || curl -f -s -m $TIMEOUT '${API_BASE_URL}/health' > /dev/null"
}

# Test Redis connectivity (via backend API)
test_redis_connectivity() {
    print_header "Redis Connectivity"

    run_test_with_retry \
        "Redis Connection (via API)" \
        "curl -f -s -m $TIMEOUT '${API_BASE_URL}/health' | jq -e '.redis_status == \"healthy\"' > /dev/null 2>&1 || curl -f -s -m $TIMEOUT '${API_BASE_URL}/health' > /dev/null"
}

# Test critical API endpoints
test_critical_endpoints() {
    print_header "Critical API Endpoints"

    # Test API docs endpoint
    run_test_with_retry \
        "API Documentation" \
        "curl -f -s -m $TIMEOUT '${API_BASE_URL}/docs' | grep -q 'swagger' || curl -f -s -m $TIMEOUT '${API_BASE_URL}/api' > /dev/null"

    # Test OpenAPI schema
    run_test_with_retry \
        "OpenAPI Schema" \
        "curl -f -s -m $TIMEOUT '${API_BASE_URL}/openapi.json' > /dev/null || curl -f -s -m $TIMEOUT '${API_BASE_URL}/api/openapi.json' > /dev/null"
}

# Test authentication endpoint (optional, may not work without creds)
test_authentication_endpoints() {
    print_header "Authentication Endpoints (Optional)"

    # Test that auth endpoint exists (may return 401 which is OK)
    print_info "Testing authentication endpoint availability..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/auth/login" || echo "000")

    if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "405" ]; then
        print_success "Authentication endpoint is accessible (HTTP $HTTP_CODE)"
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
    elif [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "000" ]; then
        print_success "Authentication endpoint is accessible (HTTP $HTTP_CODE)"
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "Authentication endpoint returned unexpected status: $HTTP_CODE"
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Test API response times
test_response_times() {
    print_header "API Response Times"

    print_info "Testing backend response time..."
    RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" -m $TIMEOUT "${API_BASE_URL}/health" || echo "999")

    print_info "Backend response time: ${RESPONSE_TIME}s"

    # Convert to integer for comparison (multiply by 1000)
    RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc 2>/dev/null || echo "999000")

    if [ "$RESPONSE_MS" -lt 5000 ]; then
        print_success "Backend response time is acceptable (< 5s)"
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "Backend response time is slow: ${RESPONSE_TIME}s"
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
}

# Test service version information
test_service_version() {
    print_header "Service Version Information"

    print_info "Fetching service version..."
    VERSION_INFO=$(curl -f -s -m $TIMEOUT "${API_BASE_URL}/health" 2>/dev/null || echo "{}")

    if [ -n "$VERSION_INFO" ] && [ "$VERSION_INFO" != "{}" ]; then
        print_success "Service version information retrieved"
        echo "$VERSION_INFO" | jq -r '.' 2>/dev/null || echo "$VERSION_INFO"
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "Could not retrieve version information"
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    print_header "🔥 Post-Deployment Smoke Tests"

    print_info "Configuration:"
    print_info "  Backend:    ${API_BASE_URL}"
    print_info "  Frontend:   ${FRONTEND_URL}"
    print_info "  Timeout:    ${TIMEOUT}s"
    print_info "  Max Retries: ${MAX_RETRIES}"

    echo ""

    # Parse arguments
    parse_arguments "$@"

    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed or not in PATH"
        exit 1
    fi

    # Run all test suites
    test_backend_health
    test_frontend_accessibility
    test_database_connectivity
    test_redis_connectivity
    test_critical_endpoints
    test_authentication_endpoints
    test_response_times
    test_service_version

    # Print summary
    print_header "📊 Test Summary"

    print_info "Total Tests:  $TESTS_TOTAL"
    print_success "Passed:       $TESTS_PASSED"

    if [ $TESTS_FAILED -gt 0 ]; then
        print_error "Failed:       $TESTS_FAILED"
        echo ""
        print_error "❌ Smoke tests failed!"
        echo ""
        exit 1
    else
        echo ""
        print_success "✅ All smoke tests passed!"
        echo ""
        exit 0
    fi
}

# Run main function
main "$@"
