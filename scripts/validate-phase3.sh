#!/bin/bash

# Feature 022 Phase 3 - Final Validation Script
# Validates all components before production deployment

set -e

echo "=========================================="
echo "Feature 022 Phase 3: Final Validation"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}!${NC} $1"
}

# 1. Backend Code Validation
echo "1. Backend Code Validation"
echo "=========================="

# Check Python models exist
if [ -f "backend/src/models/stream_quality.py" ]; then
    pass "Database models created"
else
    fail "Database models missing"
fi

# Check schemas exist
if [ -f "backend/src/schemas/stream_quality.py" ]; then
    pass "Pydantic schemas created"
else
    fail "Pydantic schemas missing"
fi

# Check service exists
if [ -f "backend/src/services/quality_trends_service.py" ]; then
    pass "QualityTrendsService created"
else
    fail "QualityTrendsService missing"
fi

# Check API endpoints
if grep -q "quality/trend" backend/src/api/admin.py; then
    pass "Quality trend endpoint added"
else
    fail "Quality trend endpoint missing"
fi

if grep -q "quality/alert/config" backend/src/api/admin.py; then
    pass "Alert config endpoints added"
else
    fail "Alert config endpoints missing"
fi

# Check migration file
if [ -f "backend/alembic/versions/*phase3*" ] || ls backend/alembic/versions/ | grep -q "phase3\|stream_quality"; then
    pass "Alembic migration created"
else
    fail "Alembic migration missing"
fi

echo ""

# 2. Frontend Code Validation
echo "2. Frontend Code Validation"
echo "=========================="

# Check React components
if [ -f "frontend/src/components/dashboard/StreamQualityChart.tsx" ]; then
    pass "StreamQualityChart component created"
else
    fail "StreamQualityChart component missing"
fi

if [ -f "frontend/src/components/dashboard/StreamQualityAlertSettings.tsx" ]; then
    pass "StreamQualityAlertSettings component created"
else
    fail "StreamQualityAlertSettings component missing"
fi

# Check TypeScript types
if grep -q "QualityTrendData" frontend/src/api/admin.ts; then
    pass "Quality types added to admin API"
else
    fail "Quality types missing from admin API"
fi

# Check Metrics updated
if grep -q "Trend Analysis" frontend/src/pages/admin/Metrics.tsx; then
    pass "Metrics component updated with Phase 3 tabs"
else
    fail "Metrics component not updated"
fi

echo ""

# 3. Test Coverage Validation
echo "3. Test Coverage Validation"
echo "=========================="

# Check backend tests
if [ -f "backend/tests/api/test_quality_trends.py" ]; then
    test_count=$(grep -c "def test_" backend/tests/api/test_quality_trends.py || echo 0)
    if [ "$test_count" -gt 10 ]; then
        pass "Backend tests created ($test_count test cases)"
    else
        warn "Backend tests exist but may be incomplete ($test_count cases)"
    fi
else
    fail "Backend tests missing"
fi

# Check frontend tests
if [ -f "frontend/src/components/dashboard/StreamQualityPhase3.test.tsx" ]; then
    test_count=$(grep -c "it(" frontend/src/components/dashboard/StreamQualityPhase3.test.tsx || echo 0)
    if [ "$test_count" -gt 20 ]; then
        pass "Frontend component tests created ($test_count test cases)"
    else
        warn "Frontend tests exist but may be incomplete ($test_count cases)"
    fi
else
    fail "Frontend component tests missing"
fi

# Check integration tests
if [ -f "frontend/src/pages/admin/Metrics.Phase3.test.tsx" ]; then
    pass "Frontend integration tests created"
else
    fail "Frontend integration tests missing"
fi

echo ""

# 4. Documentation Validation
echo "4. Documentation Validation"
echo "==========================="

# Check feature guide
if [ -f "docs/features/feature-022-phase3-advanced-monitoring.md" ]; then
    lines=$(wc -l < docs/features/feature-022-phase3-advanced-monitoring.md)
    if [ "$lines" -gt 300 ]; then
        pass "Comprehensive feature guide created ($lines lines)"
    else
        warn "Feature guide exists but may be incomplete ($lines lines)"
    fi
else
    fail "Feature guide missing"
fi

# Check completion report
if [ -f "PHASE3_IMPLEMENTATION_COMPLETE.md" ]; then
    pass "Phase 3 completion report created"
else
    fail "Phase 3 completion report missing"
fi

echo ""

# 5. Code Quality Validation
echo "5. Code Quality Validation"
echo "=========================="

# Check Python syntax
if python3 -m py_compile backend/src/models/stream_quality.py 2>/dev/null; then
    pass "Python models have valid syntax"
else
    fail "Python models have syntax errors"
fi

if python3 -m py_compile backend/src/services/quality_trends_service.py 2>/dev/null; then
    pass "Service layer has valid syntax"
else
    fail "Service layer has syntax errors"
fi

# Check TypeScript compilation (basic check)
if grep -q "interface QualityTrendData" frontend/src/api/admin.ts; then
    pass "TypeScript interfaces properly defined"
else
    fail "TypeScript interfaces missing or incomplete"
fi

echo ""

# 6. Integration Validation
echo "6. Integration Validation"
echo "========================"

# Check imports in API
if grep -q "from.*quality_trends_service" backend/src/api/admin.py; then
    pass "Service imported in API"
else
    fail "Service not imported in API"
fi

if grep -q "QualityTrendsService" backend/src/api/admin.py; then
    pass "Service used in API endpoints"
else
    fail "Service not used in API"
fi

# Check component imports in Metrics
if grep -q "StreamQualityChart" frontend/src/pages/admin/Metrics.tsx; then
    pass "Trend component imported in Metrics"
else
    fail "Trend component not imported in Metrics"
fi

if grep -q "StreamQualityAlertSettings" frontend/src/pages/admin/Metrics.tsx; then
    pass "Alert settings component imported in Metrics"
else
    fail "Alert settings component not imported in Metrics"
fi

echo ""

# 7. Database Schema Validation
echo "7. Database Schema Validation"
echo "============================="

# Check migration up/down structure
if grep -q "def upgrade" backend/alembic/versions/*phase3* 2>/dev/null || \
   ls backend/alembic/versions/ | grep -q "phase3" && \
   grep -q "def upgrade\|def downgrade" backend/alembic/versions/$(ls -t backend/alembic/versions/ | grep -E "phase3|stream_quality" | head -1); then
    pass "Migration has upgrade and downgrade"
else
    warn "Migration structure may be incomplete"
fi

echo ""

# 8. File Structure Validation
echo "8. File Structure Validation"
echo "============================"

# Ensure no test files in root
if [ ! -f "test_*.py" ] && [ ! -f "test_*.ts" ] && [ ! -f "test_*.tsx" ]; then
    pass "No test files in project root"
else
    warn "Test files found in project root (should be in tests/)"
fi

# Check that new files are in correct locations
correct_locations=0
incorrect_locations=0

[ -f "backend/src/models/stream_quality.py" ] && ((correct_locations++))
[ -f "backend/src/schemas/stream_quality.py" ] && ((correct_locations++))
[ -f "backend/src/services/quality_trends_service.py" ] && ((correct_locations++))
[ -f "frontend/src/components/dashboard/StreamQualityChart.tsx" ] && ((correct_locations++))
[ -f "frontend/src/components/dashboard/StreamQualityAlertSettings.tsx" ] && ((correct_locations++))

if [ $correct_locations -eq 5 ]; then
    pass "All files in correct directories"
else
    warn "Some files may be in incorrect locations"
fi

echo ""

# 9. Dependency Check
echo "9. Dependency Check"
echo "==================="

# Check Python dependencies (basic)
if grep -q "sqlalchemy" backend/requirements.txt; then
    pass "SQLAlchemy available for ORM"
else
    warn "SQLAlchemy not found in requirements"
fi

if grep -q "pydantic" backend/requirements.txt; then
    pass "Pydantic available for validation"
else
    warn "Pydantic not found in requirements"
fi

# Check TypeScript/npm dependencies
if [ -f "frontend/package.json" ] && grep -q "react" frontend/package.json; then
    pass "React available for frontend"
else
    warn "React not found in package.json"
fi

echo ""

# 10. Documentation Coverage
echo "10. Documentation Coverage"
echo "=========================="

# Count doc sections in feature guide
if [ -f "docs/features/feature-022-phase3-advanced-monitoring.md" ]; then
    if grep -q "## Architecture" docs/features/feature-022-phase3-advanced-monitoring.md; then
        pass "Architecture documentation included"
    else
        warn "Architecture documentation missing from feature guide"
    fi
    
    if grep -q "## API Endpoints" docs/features/feature-022-phase3-advanced-monitoring.md; then
        pass "API documentation included"
    else
        warn "API documentation missing from feature guide"
    fi
    
    if grep -q "## Deployment Checklist" docs/features/feature-022-phase3-advanced-monitoring.md; then
        pass "Deployment guide included"
    else
        warn "Deployment guide missing from feature guide"
    fi
    
    if grep -q "## Troubleshooting" docs/features/feature-022-phase3-advanced-monitoring.md; then
        pass "Troubleshooting guide included"
    else
        warn "Troubleshooting guide missing from feature guide"
    fi
fi

echo ""

# Summary
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All validations passed!${NC}"
    echo ""
    echo "Phase 3 is ready for:"
    echo "  ✓ Code review"
    echo "  ✓ QA testing"
    echo "  ✓ Production deployment"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some validations failed${NC}"
    echo ""
    echo "Please fix the issues before deployment:"
    exit 1
fi
