#!/bin/bash

# Script to run all tests and generate coverage reports
# Usage: ./scripts/run-tests.sh [backend|frontend|all]

set -e

BACKEND_COV_TARGET=70
FRONTEND_COV_TARGET=60

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
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

# Backend tests
run_backend_tests() {
    print_header "Running Backend Tests"
    
    cd "$PROJECT_ROOT/backend"
    
    # Check if venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "Virtual environment not activated"
        if [ -f "../venv/Scripts/activate" ]; then
            print_warning "Activating venv..."
            source ../venv/Scripts/activate
        elif [ -f "../venv/bin/activate" ]; then
            source ../venv/bin/activate
        else
            print_error "Virtual environment not found at ../venv"
            return 1
        fi
    fi
    
    # Install test dependencies
    print_warning "Installing test dependencies..."
    pip install -q pytest pytest-cov pytest-asyncio pytest-timeout pytest-xdist
    
    # Run tests with coverage
    print_warning "Running pytest with coverage..."
    python -m pytest \
        --cov=src \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        --cov-report=json:coverage.json \
        --cov-fail-under=$BACKEND_COV_TARGET \
        --maxfail=10 \
        -v
    
    BACKEND_EXIT_CODE=$?
    
    if [ $BACKEND_EXIT_CODE -eq 0 ]; then
        print_success "Backend tests passed!"
        print_success "Coverage report: backend/htmlcov/index.html"
    else
        print_error "Backend tests failed (exit code: $BACKEND_EXIT_CODE)"
        return $BACKEND_EXIT_CODE
    fi
}

# Frontend tests
run_frontend_tests() {
    print_header "Running Frontend Tests"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_warning "Installing frontend dependencies..."
        npm install --legacy-peer-deps
    fi
    
    # Run tests with coverage
    print_warning "Running vitest with coverage..."
    npm run test:coverage
    
    FRONTEND_EXIT_CODE=$?
    
    if [ $FRONTEND_EXIT_CODE -eq 0 ]; then
        print_success "Frontend tests passed!"
        print_success "Coverage report: frontend/coverage/index.html"
    else
        print_error "Frontend tests failed (exit code: $FRONTEND_EXIT_CODE)"
        return $FRONTEND_EXIT_CODE
    fi
}

# E2E tests
run_e2e_tests() {
    print_header "Running E2E Tests (Playwright)"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Check if Playwright is installed
    if [ ! -d "node_modules/@playwright" ]; then
        print_warning "Installing Playwright..."
        npx playwright install
    fi
    
    # Run E2E tests
    print_warning "Running Playwright tests..."
    npm run test:e2e
    
    E2E_EXIT_CODE=$?
    
    if [ $E2E_EXIT_CODE -eq 0 ]; then
        print_success "E2E tests passed!"
    else
        print_error "E2E tests failed (exit code: $E2E_EXIT_CODE)"
        return $E2E_EXIT_CODE
    fi
}

# Generate combined report
generate_report() {
    print_header "Generating Combined Test Report"
    
    # TODO: Parse coverage.json and generate markdown report
    print_warning "Combined report generation: TODO"
}

# Main execution
main() {
    local TEST_TARGET="${1:-all}"
    local BACKEND_PASSED=0
    local FRONTEND_PASSED=0
    local E2E_PASSED=0
    
    print_header "🧪 Test Suite Runner"
    echo "Target: $TEST_TARGET"
    echo "Backend coverage target: ${BACKEND_COV_TARGET}%"
    echo "Frontend coverage target: ${FRONTEND_COV_TARGET}%"
    
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
        *)
            print_error "Unknown target: $TEST_TARGET"
            echo "Usage: $0 [backend|frontend|e2e|all]"
            exit 1
            ;;
    esac
    
    # Summary
    print_header "📊 Test Summary"
    
    if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "backend" ]; then
        if [ $BACKEND_PASSED -eq 0 ]; then
            print_success "Backend: PASSED"
        else
            print_error "Backend: FAILED"
        fi
    fi
    
    if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "frontend" ]; then
        if [ $FRONTEND_PASSED -eq 0 ]; then
            print_success "Frontend: PASSED"
        else
            print_error "Frontend: FAILED"
        fi
    fi
    
    if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "e2e" ]; then
        if [ $E2E_PASSED -eq 0 ]; then
            print_success "E2E: PASSED"
        else
            print_error "E2E: FAILED"
        fi
    fi
    
    # Exit with error if any tests failed
    if [ $BACKEND_PASSED -ne 0 ] || [ $FRONTEND_PASSED -ne 0 ] || [ $E2E_PASSED -ne 0 ]; then
        print_error "Some tests failed!"
        exit 1
    fi
    
    print_success "All tests passed! 🎉"
}

# Run main with arguments
main "$@"
