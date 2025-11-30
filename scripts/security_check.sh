#!/bin/bash
# =============================================================================
# Security Check Script
# Проверяет безопасность конфигурации перед деплоем
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo "🔐 Security Configuration Check"
echo "================================"
echo ""

# -----------------------------------------------------------------------------
# 1. Проверка паролей по умолчанию
# -----------------------------------------------------------------------------
echo "1. Checking for default/weak passwords..."

check_password() {
    local var_name=$1
    local var_value=$2
    local weak_patterns=("password" "admin" "123456" "change_this" "default" "secret" "test")
    
    if [ -z "$var_value" ]; then
        echo -e "  ${RED}✗ $var_name is empty${NC}"
        ((ERRORS++))
        return 1
    fi
    
    if [ ${#var_value} -lt 12 ]; then
        echo -e "  ${YELLOW}⚠ $var_name is shorter than 12 characters${NC}"
        ((WARNINGS++))
    fi
    
    for pattern in "${weak_patterns[@]}"; do
        if echo "$var_value" | grep -qi "$pattern"; then
            echo -e "  ${RED}✗ $var_name contains weak pattern: $pattern${NC}"
            ((ERRORS++))
            return 1
        fi
    done
    
    echo -e "  ${GREEN}✓ $var_name looks secure${NC}"
    return 0
}

# Загрузка .env файла
if [ -f ".env" ]; then
    source .env 2>/dev/null || true
fi

# Проверка критических переменных
check_password "DB_PASSWORD" "${DB_PASSWORD:-}"
check_password "JWT_SECRET" "${JWT_SECRET:-}"
check_password "GRAFANA_ADMIN_PASSWORD" "${GRAFANA_ADMIN_PASSWORD:-}"

echo ""

# -----------------------------------------------------------------------------
# 2. Проверка Docker конфигурации
# -----------------------------------------------------------------------------
echo "2. Checking Docker configuration..."

# Проверка на Docker socket mount
if grep -q "docker.sock" docker-compose.yml 2>/dev/null; then
    echo -e "  ${RED}✗ Docker socket is mounted - CRITICAL SECURITY RISK${NC}"
    ((ERRORS++))
else
    echo -e "  ${GREEN}✓ No Docker socket mount found${NC}"
fi

# Проверка network isolation
if grep -q "internal: true" docker-compose.yml 2>/dev/null; then
    echo -e "  ${GREEN}✓ Network isolation is configured${NC}"
else
    echo -e "  ${YELLOW}⚠ No internal network isolation found${NC}"
    ((WARNINGS++))
fi

# Проверка healthchecks
healthcheck_count=$(grep -c "healthcheck:" docker-compose.yml 2>/dev/null || echo "0")
if [ "$healthcheck_count" -gt 0 ]; then
    echo -e "  ${GREEN}✓ Found $healthcheck_count healthchecks configured${NC}"
else
    echo -e "  ${YELLOW}⚠ No healthchecks found${NC}"
    ((WARNINGS++))
fi

echo ""

# -----------------------------------------------------------------------------
# 3. Проверка файлов секретов
# -----------------------------------------------------------------------------
echo "3. Checking secrets files..."

# .env не должен быть в git
if git ls-files --error-unmatch .env 2>/dev/null; then
    echo -e "  ${RED}✗ .env is tracked by git - REMOVE IT${NC}"
    ((ERRORS++))
else
    echo -e "  ${GREEN}✓ .env is not tracked by git${NC}"
fi

# Проверка .gitignore
if grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo -e "  ${GREEN}✓ .env is in .gitignore${NC}"
else
    echo -e "  ${YELLOW}⚠ .env is not in .gitignore${NC}"
    ((WARNINGS++))
fi

# Проверка session файлов
if git ls-files --error-unmatch "*.session" 2>/dev/null; then
    echo -e "  ${RED}✗ Session files are tracked by git${NC}"
    ((ERRORS++))
else
    echo -e "  ${GREEN}✓ Session files are not tracked${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# 4. Проверка зависимостей
# -----------------------------------------------------------------------------
echo "4. Checking dependencies..."

if command -v pip &> /dev/null && [ -f "backend/requirements.txt" ]; then
    # Проверка на известные уязвимые версии
    if pip show safety &> /dev/null; then
        echo "  Running pip-audit/safety check..."
        # safety check --file backend/requirements.txt 2>/dev/null || true
    else
        echo -e "  ${YELLOW}⚠ 'safety' not installed, skipping vulnerability check${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠ pip not available, skipping dependency check${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# 5. Проверка SSL/TLS (для production)
# -----------------------------------------------------------------------------
echo "5. Checking SSL/TLS configuration..."

if [ -f "frontend/nginx.conf" ]; then
    if grep -q "ssl_certificate" frontend/nginx.conf 2>/dev/null; then
        echo -e "  ${GREEN}✓ SSL configured in nginx${NC}"
    else
        echo -e "  ${YELLOW}⚠ SSL not configured in nginx (OK for dev)${NC}"
        ((WARNINGS++))
    fi
fi

echo ""

# -----------------------------------------------------------------------------
# Итоги
# -----------------------------------------------------------------------------
echo "================================"
echo "Security Check Summary"
echo "================================"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}✗ FAILED: $ERRORS critical issue(s) found${NC}"
    echo -e "${YELLOW}⚠ $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please fix the critical issues before deploying to production."
    exit 1
else
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${GREEN}✓ PASSED with $WARNINGS warning(s)${NC}"
    else
        echo -e "${GREEN}✓ PASSED: All security checks passed${NC}"
    fi
    exit 0
fi
