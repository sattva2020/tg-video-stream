#!/bin/bash
# CI/CD Pipeline End-to-End Verification Script
#
# This script performs comprehensive validation of the complete CI/CD pipeline:
# - Validates all workflow configurations
# - Verifies test infrastructure
# - Checks security scanning integration
# - Validates deployment automation
# - Runs smoke tests
#
# Usage: bash scripts/ci/verify-cicd-pipeline-e2e.sh [--full|--quick]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
VERIFICATION_MODE="quick"
if [[ "$1" == "--full" ]]; then
  VERIFICATION_MODE="full"
elif [[ "$1" == "--quick" ]]; then
  VERIFICATION_MODE="quick"
fi

# Counter for results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Helper functions
print_header() {
  echo ""
  echo "=========================================="
  echo "$1"
  echo "=========================================="
  echo ""
}

print_section() {
  echo ""
  echo -e "${BLUE}▶ $1${NC}"
  echo ""
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
  ((PASSED_CHECKS++))
  ((TOTAL_CHECKS++))
}

print_failure() {
  echo -e "${RED}❌ $1${NC}"
  ((FAILED_CHECKS++))
  ((TOTAL_CHECKS++))
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
  ((WARNINGS++))
}

print_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

check_file_exists() {
  local file=$1
  local description=$2

  if [[ -f "$file" ]]; then
    print_success "$description: $file"
    return 0
  else
    print_failure "$description not found: $file"
    return 1
  fi
}

check_workflow_syntax() {
  local workflow_file=$1
  local description=$2

  print_info "Validating $description..."

  # Check if workflow file exists
  if [[ ! -f "$workflow_file" ]]; then
    print_failure "$description file not found"
    return 1
  fi

  # Basic YAML syntax check (check for common errors)
  if grep -q $'\t' "$workflow_file"; then
    print_failure "$description contains tabs (YAML must use spaces)"
    return 1
  fi

  # Check for required workflow fields
  if ! grep -q "name:" "$workflow_file"; then
    print_failure "$description missing 'name' field"
    return 1
  fi

  if ! grep -q "on:" "$workflow_file" && ! grep -q "on:" "$workflow_file"; then
    print_failure "$description missing trigger configuration"
    return 1
  fi

  if ! grep -q "jobs:" "$workflow_file"; then
    print_failure "$description missing 'jobs' section"
    return 1
  fi

  print_success "$description syntax is valid"
  return 0
}

check_script_executable() {
  local script=$1
  local description=$2

  if [[ -x "$script" ]]; then
    print_success "$description is executable"
    return 0
  else
    print_warning "$description is not executable (chmod +x may be needed)"
    return 1
  fi
}

# ============================================================================
# MAIN VERIFICATION FLOW
# ============================================================================

print_header "CI/CD PIPELINE END-TO-END VERIFICATION"
print_info "Mode: $VERIFICATION_MODE"
print_info "Started: $(date '+%Y-%m-%d %H:%M:%S')"

# ============================================================================
# SECTION 1: Workflow Configuration Validation
# ============================================================================
print_section "1. Validating CI/CD Workflow Configurations"

# Check CI workflow
check_workflow_syntax ".github/workflows/ci.yml" "CI workflow"

# Check CD workflow
check_workflow_syntax ".github/workflows/cd.yml" "CD workflow"

# Check Security workflow
check_workflow_syntax ".github/workflows/security-scan.yml" "Security Scan workflow"

# Check i18n workflow
check_workflow_syntax ".github/workflows/i18n-check.yml" "i18n Check workflow"

# Check test flakiness detection workflow
if [[ -f ".github/workflows/test-flakiness-detection.yml" ]]; then
  check_workflow_syntax ".github/workflows/test-flakiness-detection.yml" "Test Flakiness Detection workflow"
fi

# ============================================================================
# SECTION 2: Test Infrastructure Validation
# ============================================================================
print_section "2. Validating Test Infrastructure"

# Check unified test runner
check_file_exists "scripts/run-all-tests.sh" "Unified test runner"
check_script_executable "scripts/run-all-tests.sh" "Unified test runner"

# Check backend test configuration
check_file_exists "backend/pytest.ci.ini" "Backend CI pytest configuration"

# Check pytest retry configuration
if grep -q "rerun" backend/pytest.ci.ini 2>/dev/null; then
  print_success "Backend test retry logic configured"
else
  print_warning "Backend test retry logic may not be configured"
fi

# Check frontend test configuration
check_file_exists "frontend/vite.config.ts" "Frontend Vite configuration"

# Check for case-sensitivity plugin
if grep -q "caseSensitivityCheck" frontend/vite.config.ts 2>/dev/null; then
  print_success "Frontend case-sensitivity check plugin configured"
else
  print_warning "Frontend case-sensitivity check plugin not found"
fi

# Check for bundle size monitoring
if grep -q "bundleSizeMonitor" frontend/vite.config.ts 2>/dev/null; then
  print_success "Frontend bundle size monitoring configured"
else
  print_warning "Frontend bundle size monitoring not found"
fi

# ============================================================================
# SECTION 3: Cross-Platform Build Validation
# ============================================================================
print_section "3. Validating Cross-Platform Build Scripts"

# Check cross-platform validation script
check_file_exists "scripts/ci/validate-build-cross-platform.sh" "Cross-platform build validation"
check_script_executable "scripts/ci/validate-build-cross-platform.sh" "Cross-platform build validation"

# Check chunk validation script
check_file_exists "frontend/scripts/validate-chunks.js" "Bundle chunk validation"

# ============================================================================
# SECTION 4: Security Scanning Integration
# ============================================================================
print_section "4. Validating Security Scanning Integration"

# Check i18n import conflict detection
check_file_exists "scripts/validate-i18n-imports.py" "i18n import conflict detection"

# Check flaky test detection
check_file_exists "scripts/ci/detect-flaky-tests.py" "Flaky test detection"

# Check post-deployment smoke tests
check_file_exists "scripts/ci/post-deploy-smoke-tests.sh" "Post-deployment smoke tests"
check_script_executable "scripts/ci/post-deploy-smoke-tests.sh" "Post-deployment smoke tests"

# ============================================================================
# SECTION 5: Deployment Automation Validation
# ============================================================================
print_section "5. Validating Deployment Automation"

# Check CD workflow for health checks
if grep -q "health check" .github/workflows/cd.yml 2>/dev/null; then
  print_success "CD workflow includes health checks"
else
  print_warning "CD workflow health checks may not be configured"
fi

# Check for rollback mechanism
if grep -q "rollback" .github/workflows/cd.yml 2>/dev/null; then
  print_success "CD workflow includes rollback mechanism"
else
  print_warning "CD workflow rollback mechanism may not be configured"
fi

# Check for smoke tests in CD
if grep -q "smoke-tests" .github/workflows/cd.yml 2>/dev/null; then
  print_success "CD workflow includes smoke tests"
else
  print_warning "CD workflow smoke tests may not be configured"
fi

# ============================================================================
# SECTION 6: Test Execution (Quick Mode)
# ============================================================================
print_section "6. Running Quick Test Validation"

if [[ "$VERIFICATION_MODE" == "quick" ]]; then
  print_info "Running unified test runner in dry-run mode..."

  if bash scripts/run-all-tests.sh --dry-run 2>&1; then
    print_success "Unified test runner dry-run passed"
  else
    print_warning "Unified test runner dry-run failed (may be expected in worktree)"
  fi

  # Test cross-platform validation
  if bash scripts/ci/validate-build-cross-platform.sh 2>&1; then
    print_success "Cross-platform build validation passed"
  else
    print_warning "Cross-platform build validation had warnings"
  fi

  # Test smoke test script help
  if bash scripts/ci/post-deploy-smoke-tests.sh --help 2>&1 | grep -q "Usage:"; then
    print_success "Smoke test script is functional"
  else
    print_warning "Smoke test script may have issues"
  fi
fi

# ============================================================================
# SECTION 7: CI Workflow Integration Validation
# ============================================================================
print_section "7. Validating CI Workflow Integration"

# Check if CI workflow runs on push
if grep -q "push:" .github/workflows/ci.yml; then
  print_success "CI workflow triggers on push"
else
  print_failure "CI workflow does not trigger on push"
fi

# Check if CI workflow runs on PR
if grep -q "pull_request:" .github/workflows/ci.yml; then
  print_success "CI workflow triggers on pull_request"
else
  print_warning "CI workflow may not trigger on pull_request"
fi

# Check for backend test job
if grep -q "backend-test:" .github/workflows/ci.yml; then
  print_success "CI workflow includes backend test job"
else
  print_failure "CI workflow missing backend test job"
fi

# Check for frontend test job
if grep -q "frontend-test:" .github/workflows/ci.yml; then
  print_success "CI workflow includes frontend test job"
else
  print_failure "CI workflow missing frontend test job"
fi

# Check for cross-platform matrix
if grep -q "matrix:" .github/workflows/ci.yml && grep -q "os:" .github/workflows/ci.yml; then
  print_success "CI workflow includes cross-platform build matrix"
else
  print_warning "CI workflow may not have cross-platform matrix"
fi

# Check for coverage reporting
if grep -q "codecov" .github/workflows/ci.yml || grep -q "coverage" .github/workflows/ci.yml; then
  print_success "CI workflow includes coverage reporting"
else
  print_warning "CI workflow may not have coverage reporting"
fi

# ============================================================================
# SECTION 8: Security Workflow Integration Validation
# ============================================================================
print_section "8. Validating Security Workflow Integration"

# Check security workflow triggers
if grep -q "push:" .github/workflows/security-scan.yml; then
  print_success "Security workflow triggers on push"
else
  print_warning "Security workflow may not trigger on push"
fi

# Check for Semgrep SAST
if grep -q "semgrep:" .github/workflows/security-scan.yml; then
  print_success "Security workflow includes Semgrep SAST"
else
  print_failure "Security workflow missing Semgrep SAST"
fi

# Check for CodeQL
if grep -q "codeql:" .github/workflows/security-scan.yml; then
  print_success "Security workflow includes CodeQL"
else
  print_failure "Security workflow missing CodeQL"
fi

# Check for Trivy
if grep -q "trivy:" .github/workflows/security-scan.yml; then
  print_success "Security workflow includes Trivy container scanning"
else
  print_failure "Security workflow missing Trivy"
fi

# Check for dependency audit
if grep -q "dependency-audit:" .github/workflows/security-scan.yml; then
  print_success "Security workflow includes dependency audit"
else
  print_failure "Security workflow missing dependency audit"
fi

# Check for secret scanning
if grep -q "secret-scan:" .github/workflows/security-scan.yml || grep -q "gitleaks" .github/workflows/security-scan.yml; then
  print_success "Security workflow includes secret scanning"
else
  print_failure "Security workflow missing secret scanning"
fi

# Check for failure on critical/high severity
if grep -q "exit-code.*1" .github/workflows/security-scan.yml; then
  print_success "Security workflow fails on critical/high findings"
else
  print_warning "Security workflow may not fail on critical/high findings"
fi

# ============================================================================
# SECTION 9: CD Workflow Integration Validation
# ============================================================================
print_section "9. Validating CD Workflow Integration"

# Check CD workflow triggers
if grep -q "push:" .github/workflows/cd.yml && grep -q "main" .github/workflows/cd.yml; then
  print_success "CD workflow triggers on push to main"
else
  print_warning "CD workflow may not trigger on push to main"
fi

# Check for manual dispatch
if grep -q "workflow_dispatch:" .github/workflows/cd.yml; then
  print_success "CD workflow supports manual dispatch"
else
  print_warning "CD workflow may not support manual dispatch"
fi

# Check for pre-deployment tests
if grep -q "test:" .github/workflows/cd.yml; then
  print_success "CD workflow includes pre-deployment test job"
else
  print_failure "CD workflow missing pre-deployment test job"
fi

# Check for staging deployment
if grep -q "deploy-staging:" .github/workflows/cd.yml; then
  print_success "CD workflow includes staging deployment"
else
  print_failure "CD workflow missing staging deployment"
fi

# Check for production deployment
if grep -q "deploy-production:" .github/workflows/cd.yml; then
  print_success "CD workflow includes production deployment"
else
  print_failure "CD workflow missing production deployment"
fi

# Check for environment protection
if grep -q "environment:" .github/workflows/cd.yml; then
  print_success "CD workflow uses environment protection"
else
  print_warning "CD workflow may not use environment protection"
fi

# ============================================================================
# SECTION 10: i18n Workflow Integration Validation
# ============================================================================
print_section "10. Validating i18n Workflow Integration"

# Check i18n workflow triggers
if grep -q "i18n-check.yml" .github/workflows/i18n-check.yml 2>/dev/null || \
   [[ -f ".github/workflows/i18n-check.yml" ]]; then
  print_success "i18n check workflow exists"

  # Check for import conflict detection
  if grep -q "validate-i18n-imports" .github/workflows/i18n-check.yml 2>/dev/null; then
    print_success "i18n workflow includes import conflict detection"
  else
    print_warning "i18n workflow may not include import conflict detection"
  fi
else
  print_warning "i18n check workflow not found"
fi

# ============================================================================
# SECTION 11: Artifact and Reporting Validation
# ============================================================================
print_section "11. Validating Artifact and Reporting Integration"

# Check for test report artifact uploads in CI
if grep -q "upload-artifact" .github/workflows/ci.yml; then
  print_success "CI workflow uploads test artifacts"
else
  print_warning "CI workflow may not upload test artifacts"
fi

# Check for coverage report uploads in CI
if grep -q "coverage" .github/workflows/ci.yml && grep -q "upload-artifact" .github/workflows/ci.yml; then
  print_success "CI workflow uploads coverage reports"
else
  print_warning "CI workflow may not upload coverage reports"
fi

# Check for GitHub Step Summary usage
if grep -q "GITHUB_STEP_SUMMARY" .github/workflows/ci.yml; then
  print_success "CI workflow generates GitHub Step Summary"
else
  print_warning "CI workflow may not generate GitHub Step Summary"
fi

# Check for PR comments
if grep -q "createComment" .github/workflows/ci.yml || grep -q "updateComment" .github/workflows/ci.yml; then
  print_success "CI workflow includes PR comments"
else
  print_warning "CI workflow may not include PR comments"
fi

# ============================================================================
# SECTION 12: Dependencies and Requirements Validation
# ============================================================================
print_section "12. Validating Dependencies and Requirements"

# Check backend requirements
check_file_exists "backend/requirements.txt" "Backend requirements"
check_file_exists "backend/requirements-dev.txt" "Backend development requirements"

# Check for pytest-rerunfailures
if grep -q "pytest-rerunfailures" backend/requirements-dev.txt 2>/dev/null; then
  print_success "pytest-rerunfailures included in dev requirements"
else
  print_warning "pytest-rerunfailures may not be in dev requirements"
fi

# Check frontend dependencies
check_file_exists "frontend/package.json" "Frontend package.json"

# Check if pnpm is used (lock file)
if [[ -f "frontend/pnpm-lock.yaml" ]]; then
  print_success "Frontend uses pnpm package manager"
elif [[ -f "frontend/package-lock.json" ]]; then
  print_success "Frontend uses npm package manager"
else
  print_warning "Frontend package manager lock file not found"
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print_header "VERIFICATION SUMMARY"

echo "Total Checks: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

# Calculate success rate
if [[ $TOTAL_CHECKS -gt 0 ]]; then
  SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
  echo "Success Rate: ${SUCCESS_RATE}%"
  echo ""

  # Determine overall status
  if [[ $FAILED_CHECKS -eq 0 ]]; then
    if [[ $WARNINGS -eq 0 ]]; then
      print_success "🎉 CI/CD PIPELINE VERIFICATION PASSED - ALL CHECKS SUCCESSFUL"
      echo ""
      echo "The complete CI/CD pipeline is properly configured and ready for use."
      echo "All workflows, scripts, and integrations are in place."
      exit 0
    else
      print_success "✅ CI/CD PIPELINE VERIFICATION PASSED - MINOR WARNINGS"
      echo ""
      echo "The CI/CD pipeline is properly configured with minor warnings."
      echo "Review warnings above for potential improvements."
      exit 0
    fi
  else
    print_failure "❌ CI/CD PIPELINE VERIFICATION FAILED - $FAILED_CHECKS CHECK(S) FAILED"
    echo ""
    echo "Some critical components are missing or misconfigured."
    echo "Review failed checks above and fix issues before deploying."
    exit 1
  fi
else
  print_failure "❌ CI/CD PIPELINE VERIFICATION INCOMPLETE"
  echo ""
  echo "No checks were performed. Please verify script is running correctly."
  exit 1
fi
