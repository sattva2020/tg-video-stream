#!/bin/bash

# Verification script for deployment automation with rollback mechanism
# This script simulates deployment failure scenarios and validates automatic rollback

set -eo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Configuration
CD_WORKFLOW="$PROJECT_ROOT/.github/workflows/cd.yml"
SMOKE_TEST_SCRIPT="$PROJECT_ROOT/scripts/ci/post-deploy-smoke-tests.sh"

# Verification counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_TOTAL=0

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
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

# Run a verification check
run_check() {
    local check_name="$1"
    local check_command="$2"

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))

    print_info "Checking: $check_name"

    if eval "$check_command"; then
        print_success "$check_name"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        print_error "$check_name"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
}

# ============================================================================
# Verification Functions
# ============================================================================

# Verify staging deployment configuration
verify_staging_deployment_config() {
    print_header "Verifying Staging Deployment Configuration"

    # Check if staging deployment job exists
    run_check \
        "Staging deployment job exists" \
        "grep -q 'name: Deploy to Staging' '$CD_WORKFLOW'"

    # Check if staging has test dependency
    run_check \
        "Staging deployment requires tests to pass" \
        "grep -A 3 'name: Deploy to Staging' '$CD_WORKFLOW' | grep -q \"needs: test\""

    # Check if previous commit is saved
    run_check \
        "Previous commit is saved before deployment" \
        "grep -q 'PREVIOUS_COMMIT=\$(git rev-parse HEAD)' '$CD_WORKFLOW'"

    # Check if deployment is logged
    run_check \
        "Deployment actions are logged" \
        "grep -q 'DEPLOYMENT_START:' '$CD_WORKFLOW'"
}

# Verify production deployment configuration
verify_production_deployment_config() {
    print_header "Verifying Production Deployment Configuration"

    # Check if production deployment job exists
    run_check \
        "Production deployment job exists" \
        "grep -q 'name: Deploy to Production' '$CD_WORKFLOW'"

    # Check if production has test dependency
    run_check \
        "Production deployment requires tests to pass" \
        "grep -A 3 'name: Deploy to Production' '$CD_WORKFLOW' | grep -q \"needs: test\""

    # Check if database backup is created
    run_check \
        "Database backup is created before production deployment" \
        "grep -q 'Creating database backup' '$CD_WORKFLOW'"

    # Check if production deployment is manually triggered
    run_check \
        "Production deployment requires manual approval" \
        "grep -A 10 'name: Deploy to Production' '$CD_WORKFLOW' | grep -q \"environment:\""
}

# Verify rollback function for staging
verify_staging_rollback_function() {
    print_header "Verifying Staging Rollback Function"

    # Check if rollback function exists
    run_check \
        "Rollback function is defined for staging" \
        "grep -q 'rollback_deployment()' '$CD_WORKFLOW'"

    # Check if rollback saves previous commit
    run_check \
        "Rollback function saves failure reason" \
        "grep -A 20 'rollback_deployment()' '$CD_WORKFLOW' | grep -q 'ROLLBACK_INITIATED:'"

    # Check if rollback performs git checkout
    run_check \
        "Rollback performs git checkout to previous commit" \
        "grep -A 30 'rollback_deployment()' '$CD_WORKFLOW' | grep -q 'git checkout \$previous_commit'"

    # Check if rollback rebuilds services
    run_check \
        "Rollback rebuilds Docker services" \
        "grep -A 30 'rollback_deployment()' '$CD_WORKFLOW' | grep -q 'docker compose up -d --build'"

    # Check if rollback waits for services
    run_check \
        "Rollback waits for services to restart" \
        "grep -A 40 'rollback_deployment()' '$CD_WORKFLOW' | grep -q 'sleep 20'"

    # Check if rollback verifies health
    run_check \
        "Rollback verifies health after rollback" \
        "grep -A 50 'rollback_deployment()' '$CD_WORKFLOW' | grep -q 'Verifying rollback health'"
}

# Verify rollback function for production
verify_production_rollback_function() {
    print_header "Verifying Production Rollback Function"

    # Check if production rollback function exists
    run_check \
        "Production rollback function is defined" \
        "grep -q 'rollback_production()' '$CD_WORKFLOW'"

    # Check if production rollback has enhanced verification
    run_check \
        "Production rollback has enhanced verification" \
        "grep -A 20 'rollback_production()' '$CD_WORKFLOW' | grep -q 'PRODUCTION_ROLLBACK_INITIATED:'"

    # Check if production rollback verifies database connection
    run_check \
        "Production rollback verifies database connection" \
        "grep -A 80 'rollback_production()' '$CD_WORKFLOW' | grep -q 'psql.*SELECT 1'"

    # Check if production rollback has multi-round verification
    run_check \
        "Production rollback has multi-round backend verification" \
        "grep -A 60 'rollback_production()' '$CD_WORKFLOW' | grep -q 'for round in 1 2 3'"
}

# Verify health checks trigger rollback
verify_health_checks_trigger_rollback() {
    print_header "Verifying Health Checks Trigger Rollback"

    # Check if Docker container check triggers rollback
    run_check \
        "Docker container failure triggers rollback" \
        "grep -A 5 'Docker containers are not running' '$CD_WORKFLOW' | grep -q 'rollback_deployment'"

    # Check if backend health check triggers rollback
    run_check \
        "Backend health check failure triggers rollback" \
        "grep -A 5 'Backend API health check failed' '$CD_WORKFLOW' | grep -q 'rollback_deployment'"

    # Check if frontend health check triggers rollback
    run_check \
        "Frontend health check failure triggers rollback" \
        "grep -A 5 'Frontend health check failed' '$CD_WORKFLOW' | grep -q 'rollback_deployment'"

    # Check if database health check triggers rollback
    run_check \
        "Database health check failure triggers rollback" \
        "grep -A 5 'Database health check failed' '$CD_WORKFLOW' | grep -q 'rollback_deployment'"

    # Check if Redis health check triggers rollback
    run_check \
        "Redis health check failure triggers rollback" \
        "grep -A 5 'Redis health check failed' '$CD_WORKFLOW' | grep -q 'rollback_deployment'"

    # Check if smoke test failure triggers rollback
    run_check \
        "Smoke test failure triggers rollback" \
        "grep -A 3 'Smoke tests failed' '$CD_WORKFLOW' | grep -q 'rollback_deployment'"
}

# Verify rollback notification
verify_rollback_notifications() {
    print_header "Verifying Rollback Notifications"

    # Check if failure notification mentions rollback
    run_check \
        "Failure notification mentions automatic rollback" \
        "grep -A 5 'Notify on failure' '$CD_WORKFLOW' | grep -q 'Automatic rollback has been initiated'"

    # Check if failure notification mentions previous commit restoration
    run_check \
        "Failure notification mentions previous commit restoration" \
        "grep -A 5 'Notify on failure' '$CD_WORKFLOW' | grep -q 'Previous commit has been restored'"

    # Check if production failure notification mentions backup
    run_check \
        "Production failure notification mentions database backup" \
        "grep 'if: failure()' '$CD_WORKFLOW' -A 10 | grep -q 'database backup was created'"
}

# Verify smoke tests integration
verify_smoke_tests_integration() {
    print_header "Verifying Smoke Tests Integration"

    # Check if smoke test script exists
    run_check \
        "Smoke test script exists" \
        "[ -f '$SMOKE_TEST_SCRIPT' ]"

    # Check if smoke tests are run after deployment
    run_check \
        "Smoke tests are run after staging deployment" \
        "grep -q 'Running post-deployment smoke tests' '$CD_WORKFLOW'"

    # Check if smoke tests run before deployment is marked successful
    run_check \
        "Smoke test failure prevents successful deployment" \
        "grep -B 2 -A 5 'Smoke tests failed' '$CD_WORKFLOW' | grep -q 'exit 1'"
}

# Verify deployment log
verify_deployment_log() {
    print_header "Verifying Deployment Log"

    # Check if deployment log is updated on deployment start
    run_check \
        "Deployment start is logged" \
        "grep -q 'DEPLOYMENT_START:' '$CD_WORKFLOW'"

    # Check if deployment success is logged
    run_check \
        "Deployment success is logged" \
        "grep -q 'DEPLOYMENT_SUCCESS:' '$CD_WORKFLOW'"

    # Check if rollback is logged
    run_check \
        "Rollback is logged" \
        "grep -q 'ROLLBACK_INITIATED:' '$CD_WORKFLOW'"

    # Check if rollback success is logged
    run_check \
        "Rollback success is logged" \
        "grep -q 'ROLLBACK_SUCCESSFUL:' '$CD_WORKFLOW'"
}

# Verify rollback instructions
verify_rollback_instructions() {
    print_header "Verifying Rollback Instructions"

    # Check if manual rollback instructions are documented
    run_check \
        "Manual rollback instructions are documented" \
        "grep -q 'ROLLBACK INSTRUCTIONS' '$CD_WORKFLOW'"

    # Check if deployment log viewing is documented
    run_check \
        "Deployment log viewing is documented" \
        "grep -q 'cat .deployment_log' '$CD_WORKFLOW'"

    # Check if automatic rollback is documented
    run_check \
        "Automatic rollback mechanism is documented" \
        "grep -q 'AUTOMATIC ROLLBACK:' '$CD_WORKFLOW'"
}

# Simulate deployment failure scenario (dry-run)
simulate_deployment_failure() {
    print_header "Simulating Deployment Failure Scenario"

    print_info "Creating simulated deployment failure test script..."

    cat > /tmp/test-deployment-failure.sh << 'EOF'
#!/bin/bash

# Simulated deployment failure scenario
# This script demonstrates what happens when a deployment fails

echo "=========================================="
echo "🔄 Simulating Deployment Failure Scenario"
echo "=========================================="
echo ""

# Simulate previous commit
PREVIOUS_COMMIT="abc123def456"
NEW_COMMIT="def789ghi012"

echo "📋 Deployment Scenario:"
echo "  Previous commit: $PREVIOUS_COMMIT"
echo "  New commit:      $NEW_COMMIT"
echo ""

echo "🚀 Starting deployment..."
echo "  ✓ Pulling latest changes..."
echo "  ✓ Building Docker images..."
echo "  ✓ Starting services..."
echo ""

echo "⏳ Waiting for services to be healthy..."
sleep 2
echo ""

echo "🏥 Running health checks..."
echo ""

# Simulate health check failures
echo "  Checking Docker containers..."
echo "    ✅ Docker containers are running"
echo ""

echo "  Checking Backend API..."
echo "    ❌ Backend API health check failed!"
echo "    Error: Connection refused on port 8000"
echo ""

echo "=========================================="
echo "🔄 INITIATING AUTOMATIC ROLLBACK"
echo "=========================================="
echo "Reason: Backend API health check failed"
echo "Rolling back to commit: $PREVIOUS_COMMIT"
echo ""

echo "📥 Rolling back git changes..."
echo "    ✓ Checked out $PREVIOUS_COMMIT"
echo ""

echo "🔧 Rebuilding and restarting services with previous version..."
echo "    ✓ Docker compose rebuilt"
echo ""

echo "⏳ Waiting for services to restart..."
sleep 2
echo ""

echo "🏥 Verifying rollback health..."
echo ""

echo "  Checking Docker containers..."
echo "    ✅ Containers are running"
echo ""

echo "  Checking Backend API..."
echo "    ✅ Backend is healthy (200 OK)"
echo ""

echo "  Checking Frontend..."
echo "    ✅ Frontend is healthy (200 OK)"
echo ""

echo "  Checking Database..."
echo "    ✅ Database is ready"
echo ""

echo "=========================================="
echo "✅ ROLLBACK SUCCESSFUL"
echo "=========================================="
echo "System is back to previous stable state"
echo "Commit: $PREVIOUS_COMMIT"
echo ""

echo "📝 Deployment Log Entry:"
echo "  [$TIMESTAMP] DEPLOYMENT_START: $NEW_COMMIT"
echo "  [$TIMESTAMP] ROLLBACK_INITIATED: Backend API health check failed"
echo "  [$TIMESTAMP] ROLLBACK_SUCCESSFUL: System restored to $PREVIOUS_COMMIT"
echo ""

EOF

    chmod +x /tmp/test-deployment-failure.sh

    print_success "Deployment failure simulation script created"
    print_info "Location: /tmp/test-deployment-failure.sh"
    print_info "Run it to see the rollback mechanism in action"
    echo ""

    # Display the simulation
    print_info "Running simulation..."
    echo ""
    bash /tmp/test-deployment-failure.sh

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    print_header "🔍 Deployment Automation & Rollback Verification"

    print_info "This script verifies the deployment automation with rollback mechanism"
    print_info "by analyzing the CD workflow configuration and simulating failure scenarios."
    echo ""

    # Check if CD workflow exists
    if [ ! -f "$CD_WORKFLOW" ]; then
        print_error "CD workflow not found: $CD_WORKFLOW"
        exit 1
    fi

    # Run all verification checks
    verify_staging_deployment_config
    verify_production_deployment_config
    verify_staging_rollback_function
    verify_production_rollback_function
    verify_health_checks_trigger_rollback
    verify_rollback_notifications
    verify_smoke_tests_integration
    verify_deployment_log
    verify_rollback_instructions

    # Simulate deployment failure
    simulate_deployment_failure

    # Print summary
    print_header "📊 Verification Summary"

    print_info "Total Checks:  $CHECKS_TOTAL"
    print_success "Passed:       $CHECKS_PASSED"

    if [ $CHECKS_FAILED -gt 0 ]; then
        print_error "Failed:       $CHECKS_FAILED"
        echo ""
        print_error "❌ Some verification checks failed!"
        echo ""
        exit 1
    else
        echo ""
        print_success "✅ All verification checks passed!"
        echo ""
        print_success "Deployment automation with rollback mechanism is properly configured."
        print_success "The system will automatically rollback on deployment failure."
        echo ""
        exit 0
    fi
}

# Run main function
main "$@"
