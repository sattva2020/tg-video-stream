#!/usr/bin/env bash
# Simple E2E verification script

echo "=========================================="
echo "E2E Deployment Verification"
echo "=========================================="
echo ""

FAILURES=0

check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1"
        return 0
    else
        echo "✗ $1 NOT FOUND"
        ((FAILURES++))
        return 1
    fi
}

echo "1. Checking deployment files..."
check_file "scripts/preflight-env.sh"
check_file "scripts/deploy-unified.sh"
check_file "scripts/backup-schedule.sh"
check_file "scripts/install.sh"
check_file "docker-compose.yml"
echo ""

echo "2. Checking documentation..."
check_file "docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md"
check_file "docs/deployment/TROUBLESHOOTING.md"
check_file "docs/deployment/BACKUP_RESTORE.md"
check_file "docs/deployment/DEPLOYMENT_CHECKLIST.md"
echo ""

echo "3. Checking monitoring configuration..."
check_file "config/monitoring/grafana/dashboards/deployment-health.json"
check_file "config/monitoring/grafana/dashboards/backup-monitoring.json"
check_file "config/monitoring/rules/critical.yml"
check_file "config/monitoring/rules/warning.yml"
echo ""

echo "4. Checking systemd services..."
check_file "config/systemd/automated-backup.service"
check_file "config/systemd/automated-backup.timer"
echo ""

echo "5. Checking E2E test file..."
check_file "backend/tests/integration/test_deployment_e2e.py"
echo ""

echo "=========================================="
if [ $FAILURES -eq 0 ]; then
    echo "✓ All checks passed!"
    exit 0
else
    echo "✗ $FAILURES check(s) failed"
    exit 1
fi
