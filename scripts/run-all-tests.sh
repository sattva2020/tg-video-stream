#!/bin/bash

# Unified test runner script that executes all tests with proper exit codes and reporting
# Usage: ./scripts/run-all-tests.sh [backend|frontend|e2e|all] [--dry-run] [--ci] [--verbose]

set -eo pipefail

# Configuration
BACKEND_COV_TARGET=70
FRONTEND_COV_TARGET=60
DRY_RUN=false
CI_MODE=false
VERBOSE=false

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG] $1${NC}"
    fi
}

# Parse command line arguments
parse_arguments() {
    local TEST_TARGET="all"

    while [[ $# -gt 0 ]]; do
        case $1 in
            backend|frontend|e2e|all)
                TEST_TARGET="$1"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                print_info "Dry run mode: Commands will be printed but not executed"
                shift
                ;;
            --ci)
                CI_MODE=true
                log_verbose "CI mode enabled"
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
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

    echo "$TEST_TARGET"
}

show_help() {
    cat << EOF
Usage: $0 [backend|frontend|e2e|all] [OPTIONS]

Unified test runner script that executes all tests with proper exit codes and reporting.

Arguments:
  backend       Run backend tests only
  frontend      Run frontend unit tests only
  e2e           Run end-to-end tests only
  all           Run all tests (default)

Options:
  --dry-run     Print commands without executing them
  --ci          Enable CI mode (stricter error handling)
  --verbose, -v Enable verbose output
  --help, -h    Show this help message

Examples:
  $0                          # Run all tests
  $0 backend                  # Run backend tests only
  $0 --dry-run               # Show what would be executed
  $0 all --ci --verbose      # Run all tests in CI mode with verbose output

EOF
}

# ============================================================================
# Test Execution Functions
# ============================================================================

# Backend tests
run_backend_tests() {
    print_header "Running Backend Tests"

    local backend_dir="$PROJECT_ROOT/backend"
    local exit_code=0

    # Check if backend directory exists
    if [ ! -d "$backend_dir" ]; then
        print_error "Backend directory not found: $backend_dir"
        return 1
    fi

    cd "$backend_dir"

    # Check if venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "Virtual environment not activated"
        if [ -f "../venv/Scripts/activate" ]; then
            print_warning "Activating venv (Windows)..."
            if [ "$DRY_RUN" = false ]; then
                source ../venv/Scripts/activate
            else
                print_info "[DRY-RUN] Would activate: ../venv/Scripts/activate"
            fi
        elif [ -f "../venv/bin/activate" ]; then
            print_warning "Activating venv (Unix)..."
            if [ "$DRY_RUN" = false ]; then
                source ../venv/bin/activate
            else
                print_info "[DRY-RUN] Would activate: ../venv/bin/activate"
            fi
        else
            print_error "Virtual environment not found at ../venv"
            return 1
        fi
    fi

    # Install test dependencies
    print_warning "Installing test dependencies..."
    local pip_cmd="pip install -q pytest pytest-cov pytest-asyncio pytest-timeout pytest-xdist"
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run: $pip_cmd"
    else
        eval "$pip_cmd" || exit_code=$?
        if [ $exit_code -ne 0 ]; then
            print_error "Failed to install test dependencies"
            return $exit_code
        fi
    fi

    # Run tests with coverage
    print_warning "Running pytest with coverage..."
    local pytest_cmd="python -m pytest \
        --cov=src \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        --cov-report=json:coverage.json \
        --cov-fail-under=$BACKEND_COV_TARGET \
        --maxfail=10 \
        -v"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run: $pytest_cmd"
        print_success "Backend tests (dry-run): PASSED"
        return 0
    else
        eval "$pytest_cmd" || exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_success "Backend tests passed!"
            print_success "Coverage report: backend/htmlcov/index.html"
            print_success "Coverage JSON: backend/coverage.json"
        else
            print_error "Backend tests failed (exit code: $exit_code)"
            return $exit_code
        fi
    fi
}

# Frontend unit tests
run_frontend_tests() {
    print_header "Running Frontend Unit Tests"

    local frontend_dir="$PROJECT_ROOT/frontend"
    local exit_code=0

    # Check if frontend directory exists
    if [ ! -d "$frontend_dir" ]; then
        print_error "Frontend directory not found: $frontend_dir"
        return 1
    fi

    cd "$frontend_dir"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_warning "Installing frontend dependencies..."
        local npm_cmd="npm install --legacy-peer-deps"
        if [ "$DRY_RUN" = true ]; then
            print_info "[DRY-RUN] Would run: $npm_cmd"
        else
            eval "$npm_cmd" || exit_code=$?
            if [ $exit_code -ne 0 ]; then
                print_error "Failed to install frontend dependencies"
                return $exit_code
            fi
        fi
    fi

    # Run tests with coverage
    print_warning "Running vitest with coverage..."
    local test_cmd="npm run test:coverage"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run: $test_cmd"
        print_success "Frontend tests (dry-run): PASSED"
        return 0
    else
        eval "$test_cmd" || exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_success "Frontend tests passed!"
            print_success "Coverage report: frontend/coverage/index.html"
        else
            print_error "Frontend tests failed (exit code: $exit_code)"
            return $exit_code
        fi
    fi
}

# E2E tests
run_e2e_tests() {
    print_header "Running E2E Tests (Playwright)"

    local frontend_dir="$PROJECT_ROOT/frontend"
    local exit_code=0

    # Check if frontend directory exists
    if [ ! -d "$frontend_dir" ]; then
        print_error "Frontend directory not found: $frontend_dir"
        return 1
    fi

    cd "$frontend_dir"

    # Check if Playwright is installed
    if [ ! -d "node_modules/@playwright" ]; then
        print_warning "Installing Playwright..."
        local playwright_cmd="npx playwright install"
        if [ "$DRY_RUN" = true ]; then
            print_info "[DRY-RUN] Would run: $playwright_cmd"
        else
            eval "$playwright_cmd" || exit_code=$?
            if [ $exit_code -ne 0 ]; then
                print_error "Failed to install Playwright"
                return $exit_code
            fi
        fi
    fi

    # Run E2E tests
    print_warning "Running Playwright tests..."
    local e2e_cmd="npm run test:e2e"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would run: $e2e_cmd"
        print_success "E2E tests (dry-run): PASSED"
        return 0
    else
        eval "$e2e_cmd" || exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_success "E2E tests passed!"
        else
            print_error "E2E tests failed (exit code: $exit_code)"
            return $exit_code
        fi
    fi
}

# ============================================================================
# Reporting Functions
# ============================================================================

# Generate combined test report
generate_report() {
    print_header "Generating Combined Test Report"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would generate combined test report"
        return 0
    fi

    local report_file="$PROJECT_ROOT/test-report.md"
    local timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

    cat > "$report_file" << EOF
# Test Execution Report

**Generated:** $timestamp
**Command:** $0 $@

## Test Results Summary

| Test Suite | Status | Exit Code |
|------------|--------|-----------|
| Backend    | $([ $BACKEND_PASSED -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED") | $BACKEND_PASSED |
| Frontend   | $([ $FRONTEND_PASSED -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED") | $FRONTEND_PASSED |
| E2E        | $([ $E2E_PASSED -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED") | $E2E_PASSED |

## Coverage Reports

- Backend: [backend/htmlcov/index.html](backend/htmlcov/index.html)
- Frontend: [frontend/coverage/index.html](frontend/coverage/index.html)

## Detailed Coverage Data

EOF

    # Append backend coverage if available
    if [ -f "$PROJECT_ROOT/backend/coverage.json" ]; then
        echo "### Backend Coverage" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
        cat "$PROJECT_ROOT/backend/coverage.json" | grep -A 5 "totals" || echo "Coverage data available" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
    fi

    print_success "Test report generated: $report_file"
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    local TEST_TARGET=$(parse_arguments "$@")
    local BACKEND_PASSED=0
    local FRONTEND_PASSED=0
    local E2E_PASSED=0

    print_header "🧪 Unified Test Suite Runner"
    echo "Target: $TEST_TARGET"
    echo "Backend coverage target: ${BACKEND_COV_TARGET}%"
    echo "Frontend coverage target: ${FRONTEND_COV_TARGET}%"
    if [ "$DRY_RUN" = true ]; then
        echo "Mode: DRY-RUN (commands will not be executed)"
    fi

    # Execute tests based on target
    case "$TEST_TARGET" in
        backend)
            run_backend_tests || BACKEND_PASSED=$?
            ;;
        frontend)
            run_frontend_tests || FRONTEND_PASSED=$?
            ;;
        e2e)
            run_e2e_tests || E2E_PASSED=$?
            ;;
        all)
            run_backend_tests || BACKEND_PASSED=$?
            run_frontend_tests || FRONTEND_PASSED=$?
            run_e2e_tests || E2E_PASSED=$?
            ;;
    esac

    # Generate report if not in dry-run mode
    if [ "$DRY_RUN" = false ] && [ "$TEST_TARGET" = "all" ]; then
        generate_report
    fi

    # Print summary
    print_header "📊 Test Summary"

    local TOTAL_FAILED=0

    if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "backend" ]; then
        if [ $BACKEND_PASSED -eq 0 ]; then
            print_success "Backend: PASSED"
        else
            print_error "Backend: FAILED (exit code: $BACKEND_PASSED)"
            TOTAL_FAILED=$((TOTAL_FAILED + 1))
        fi
    fi

    if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "frontend" ]; then
        if [ $FRONTEND_PASSED -eq 0 ]; then
            print_success "Frontend: PASSED"
        else
            print_error "Frontend: FAILED (exit code: $FRONTEND_PASSED)"
            TOTAL_FAILED=$((TOTAL_FAILED + 1))
        fi
    fi

    if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "e2e" ]; then
        if [ $E2E_PASSED -eq 0 ]; then
            print_success "E2E: PASSED"
        else
            print_error "E2E: FAILED (exit code: $E2E_PASSED)"
            TOTAL_FAILED=$((TOTAL_FAILED + 1))
        fi
    fi

    # Final result
    echo ""
    if [ $TOTAL_FAILED -eq 0 ]; then
        print_success "All tests passed! 🎉"
        return 0
    else
        print_error "$TOTAL_FAILED test suite(s) failed!"
        return 1
    fi
}

# Run main function with all arguments
main "$@"
