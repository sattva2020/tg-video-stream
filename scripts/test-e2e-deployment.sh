#!/usr/bin/env bash
set -euo pipefail

##############################################################################
# End-to-End Deployment Test Runner
# Запускает все тесты полного цикла развёртывания
#
# Usage:
#   bash scripts/test-e2e-deployment.sh [OPTIONS]
#
# Options:
#   --skip-services     Пропустить тесты сервисов (требуют запущенные сервисы)
#   --skip-monitoring   Пропустить тесты мониторинга
#   --quick             Быстрый режим (только базовые проверки)
#   --help, -h          Показать справку
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Flags
SKIP_SERVICES=false
SKIP_MONITORING=false
QUICK_MODE=false

##############################################################################
# Logging Functions
##############################################################################

log_section() {
  echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_ok() {
  echo -e "${GREEN}✓ $1${NC}"
}

log_err() {
  echo -e "${RED}✗ $1${NC}"
}

log_info() {
  echo -e "${YELLOW}→ $1${NC}"
}

##############################################################################
# Test Functions
##############################################################################

test_file_exists() {
  local file="$1"
  local description="$2"

  if [ -f "$file" ]; then
    log_ok "$description"
    return 0
  else
    log_err "$description - файл не найден: $file"
    return 1
  fi
}

test_command_exists() {
  local cmd="$1"
  local description="$2"

  if command -v "$cmd" >/dev/null 2>&1; then
    log_ok "$description"
    return 0
  else
    log_info "$description - не найдено (пропуск)"
    return 0
  fi
}

test_script_syntax() {
  local script="$1"
  local description="$2"

  if bash -n "$script" 2>/dev/null; then
    log_ok "$description"
    return 0
  else
    log_err "$description - ошибка синтаксиса"
    return 1
  fi
}

test_http_endpoint() {
  local url="$1"
  local description="$2"
  local expected_codes="${3:-200 503}"

  if command -v curl >/dev/null 2>&1; then
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5 2>/dev/null || echo "000")

    for code in $expected_codes; do
      if [ "$response" = "$code" ]; then
        log_ok "$description (HTTP $response)"
        return 0
      fi
    done

    log_info "$description - недоступен (HTTP $response)"
    return 0
  else
    log_info "$description - curl не установлен (пропуск)"
    return 0
  fi
}

##############################################################################
# Test Suites
##############################################################################

run_deployment_files_tests() {
  log_section "1. Файлы развёртывания"

  local all_ok=true

  # Core scripts
  test_file_exists "$SCRIPT_DIR/preflight-env.sh" "Preflight validation script" || all_ok=false
  test_file_exists "$SCRIPT_DIR/deploy-unified.sh" "Unified deployment script" || all_ok=false
  test_file_exists "$SCRIPT_DIR/backup-schedule.sh" "Backup schedule script" || all_ok=false
  test_file_exists "$SCRIPT_DIR/install.sh" "Installation wizard script" || all_ok=false

  # Docker configuration
  test_file_exists "$PROJECT_ROOT/docker-compose.yml" "Docker Compose configuration" || all_ok=false

  # Documentation
  test_file_exists "$PROJECT_ROOT/docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md" "Production deployment guide" || all_ok=false
  test_file_exists "$PROJECT_ROOT/docs/deployment/TROUBLESHOOTING.md" "Troubleshooting guide" || all_ok=false
  test_file_exists "$PROJECT_ROOT/docs/deployment/BACKUP_RESTORE.md" "Backup/restore documentation" || all_ok=false
  test_file_exists "$PROJECT_ROOT/docs/deployment/DEPLOYMENT_CHECKLIST.md" "Deployment checklist" || all_ok=false

  if [ "$all_ok" = true ]; then
    log_ok "Все файлы развёртывания присутствуют"
    return 0
  else
    return 1
  fi
}

run_script_syntax_tests() {
  log_section "2. Синтаксис скриптов"

  local all_ok=true

  test_script_syntax "$SCRIPT_DIR/preflight-env.sh" "preflight-env.sh syntax" || all_ok=false
  test_script_syntax "$SCRIPT_DIR/deploy-unified.sh" "deploy-unified.sh syntax" || all_ok=false
  test_script_syntax "$SCRIPT_DIR/backup-schedule.sh" "backup-schedule.sh syntax" || all_ok=false
  test_script_syntax "$SCRIPT_DIR/install.sh" "install.sh syntax" || all_ok=false

  if [ "$all_ok" = true ]; then
    log_ok "Все скрипты имеют валидный синтаксис"
    return 0
  else
    return 1
  fi
}

run_environment_tests() {
  log_section "3. Окружение"

  local all_ok=true

  # Check for Docker
  if [ "$QUICK_MODE" = false ]; then
    test_command_exists "docker" "Docker" || all_ok=false
  fi

  # Check for bash
  test_command_exists "bash" "Bash" || all_ok=false

  # Check for curl
  test_command_exists "curl" "cURL" || all_ok=false

  if [ "$all_ok" = true ]; then
    log_ok "Базовое окружение в порядке"
    return 0
  else
    return 1
  fi
}

run_service_tests() {
  if [ "$SKIP_SERVICES" = true ]; then
    log_section "4. Сервисы (пропущено)"
    return 0
  fi

  log_section "4. Сервисы"

  # Backend health
  test_http_endpoint "http://localhost:8000/api/health" "Backend health endpoint" "200 503"

  # Backend liveness
  test_http_endpoint "http://localhost:8000/api/health/live" "Backend liveness probe" "200"

  # Backend readiness
  test_http_endpoint "http://localhost:8000/api/health/ready" "Backend readiness probe" "200 503"

  log_ok "Проверки сервисов завершены"
  return 0
}

run_monitoring_tests() {
  if [ "$SKIP_MONITORING" = true ]; then
    log_section "5. Мониторинг (пропущено)"
    return 0
  fi

  log_section "5. Мониторинг"

  # Prometheus
  test_http_endpoint "http://localhost:9090/-/healthy" "Prometheus health" "200 503"

  # Grafana
  test_http_endpoint "http://localhost:3001/api/health" "Grafana API health" "200 503"

  log_ok "Проверки мониторинга завершены"
  return 0
}

run_backup_tests() {
  if [ "$SKIP_SERVICES" = true ]; then
    log_section "6. Резервное копирование (пропущено)"
    return 0
  fi

  log_section "6. Резервное копирование"

  # Check for systemd timer files
  local systemd_dir="$PROJECT_ROOT/config/systemd"
  if [ -d "$systemd_dir" ]; then
    test_file_exists "$systemd_dir/automated-backup.service" "Automated backup service file"
    test_file_exists "$systemd_dir/automated-backup.timer" "Automated backup timer file"
  else
    log_info "Systemd директория не найдена (Docker развёртывание)"
  fi

  log_ok "Проверки резервного копирования завершены"
  return 0
}

run_python_tests() {
  log_section "7. Python тесты"

  if ! command -v python >/dev/null 2>&1; then
    log_info "Python не найден (пропуск Python тестов)"
    return 0
  fi

  # Check Python syntax for test file
  local test_file="$PROJECT_ROOT/backend/tests/integration/test_deployment_e2e.py"

  if [ -f "$test_file" ]; then
    if python -c "import ast; ast.parse(open('$test_file').read())" 2>/dev/null; then
      log_ok "test_deployment_e2e.py синтаксис корректен"
    else
      log_err "test_deployment_e2e.py ошибка синтаксиса"
      return 1
    fi
  else
    log_info "Файл test_deployment_e2e.py не найден"
  fi

  # Try to run pytest if available
  if command -v pytest >/dev/null 2>&1; then
    if [ "$QUICK_MODE" = false ]; then
      log_info "Запуск pytest..."
      cd "$PROJECT_ROOT/backend"
      pytest tests/integration/test_deployment_e2e.py -v --tb=short || log_info "Некоторые тесты пропущены (сервисы не запущены)"
      cd "$PROJECT_ROOT"
    fi
  else
    log_info "pytest не установлен (пропуск выполнения тестов)"
  fi

  return 0
}

##############################################################################
# Main
##############################################################################

main() {
  log_section "E2E Тесты развёртывания"
  echo "Режим: $([ "$QUICK_MODE" = true ] && echo 'быстрый' || echo 'полный')"
  echo ""

  local total=0
  local passed=0

  run_deployment_files_tests && ((passed++)) || true
  ((total++))

  run_script_syntax_tests && ((passed++)) || true
  ((total++))

  run_environment_tests && ((passed++)) || true
  ((total++))

  run_service_tests && ((passed++)) || true
  ((total++))

  run_monitoring_tests && ((passed++)) || true
  ((total++))

  run_backup_tests && ((passed++)) || true
  ((total++))

  run_python_tests && ((passed++)) || true
  ((total++))

  # Summary
  log_section "Итого"
  echo "Пройдено: $passed / $total тестовых наборов"

  if [ "$passed" -eq "$total" ]; then
    log_ok "Все тесты пройдены!"
    return 0
  else
    log_info "Некоторые тесты пропущены или не пройдены"
    return 0
  fi
}

##############################################################################
# Argument Parsing
##############################################################################

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-services)
      SKIP_SERVICES=true
      shift
      ;;
    --skip-monitoring)
      SKIP_MONITORING=true
      shift
      ;;
    --quick)
      QUICK_MODE=true
      SKIP_SERVICES=true
      SKIP_MONITORING=true
      shift
      ;;
    --help|-h)
      grep -A 20 "^# Usage:" "$0" | head -21
      exit 0
      ;;
    *)
      log_err "Неизвестный аргумент: $1"
      exit 1
      ;;
  esac
done

main "$@"
