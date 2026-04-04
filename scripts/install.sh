#!/usr/bin/env bash
set -euo pipefail

##############################################################################
# Installation Wizard Script
# One-command setup for deployment automation and health monitoring
#
# Usage:
#   bash scripts/install.sh [OPTIONS]
#
# Options:
#   --check              Check if installation is complete
#   --docker             Force Docker installation
#   --bare-metal         Force bare-metal (systemd) installation
#   --skip-deps          Skip dependency installation
#   --help, -h           Show this help
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Installation options
INSTALL_MODE=""
SKIP_DEPS=false
CHECK_ONLY=false

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
  echo -e "${RED}✗ $1${NC}" >&2
}

log_info() {
  echo -e "${YELLOW}→ $1${NC}"
}

log_step() {
  echo -e "\n${YELLOW}▶ $1${NC}"
}

##############################################################################
# Check Mode
##############################################################################

check_installation() {
  local errors=0

  log_section "Installation Check"

  # Check 1: Python
  log_step "Checking Python installation"
  if command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
    log_ok "Python is installed"
    if command -v python3 >/dev/null 2>&1; then
      python3 --version 2>/dev/null || true
    else
      python --version 2>/dev/null || true
    fi
  else
    log_err "Python not found"
    errors=$((errors + 1))
  fi

  # Check 2: Docker (if available)
  log_step "Checking Docker installation"
  if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
      log_ok "Docker is installed and running"
      docker --version 2>/dev/null || true
    else
      log_info "Docker is installed but not running"
    fi
  else
    log_info "Docker not found (optional for bare-metal deployment)"
  fi

  # Check 3: Pre-flight script
  log_step "Checking pre-flight validation script"
  if [ -f "$SCRIPT_DIR/preflight-env.sh" ]; then
    log_ok "Preflight script found"
  else
    log_err "Preflight script not found"
    errors=$((errors + 1))
  fi

  # Check 4: Configuration files
  log_step "Checking configuration files"
  if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    log_ok "docker-compose.yml found"
  else
    log_info "docker-compose.yml not found (optional for bare-metal)"
  fi

  # Check 5: Systemd units (for bare-metal)
  log_step "Checking systemd service files"
  if compgen -G "$PROJECT_ROOT/config/systemd/*.service" >/dev/null; then
    log_ok "Systemd service files found"
  else
    log_info "Systemd service files not found (optional for Docker)"
  fi

  # Check 6: Virtual environment
  log_step "Checking virtual environment"
  if [ -d "$PROJECT_ROOT/.venv" ] || [ -d "$PROJECT_ROOT/venv" ]; then
    log_ok "Virtual environment exists"
  else
    log_info "Virtual environment not found (run install without --check to create)"
  fi

  # Summary
  echo ""
  if [ $errors -eq 0 ]; then
    log_ok "Installation check passed"
    return 0
  else
    log_err "Installation check failed with $errors error(s)"
    return 1
  fi
}

##############################################################################
# Environment Detection
##############################################################################

detect_environment() {
  log_section "Environment Detection"

  local has_docker=0
  local has_bare_metal=0

  # Check Docker
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    log_ok "Docker detected and running"
    docker --version 2>/dev/null || true
    has_docker=1
  else
    log_info "Docker not available"
  fi

  # Check bare-metal prerequisites
  if command -v python3 >/dev/null 2>&1 && command -v systemctl >/dev/null 2>&1; then
    log_ok "Bare-metal prerequisites detected (python3, systemd)"
    has_bare_metal=1
  else
    log_info "Bare-metal prerequisites not met"
  fi

  # Auto-detect if not forced
  if [ -z "$INSTALL_MODE" ]; then
    if [ $has_docker -eq 1 ] && [ $has_bare_metal -eq 0 ]; then
      INSTALL_MODE="docker"
      log_info "Auto-detected: Docker deployment"
    elif [ $has_docker -eq 0 ] && [ $has_bare_metal -eq 1 ]; then
      INSTALL_MODE="bare-metal"
      log_info "Auto-detected: Bare-metal deployment"
    elif [ $has_docker -eq 1 ] && [ $has_bare_metal -eq 1 ]; then
      # Both available - prefer Docker
      INSTALL_MODE="docker"
      log_info "Auto-detected: Docker deployment (both available, Docker preferred)"
    else
      log_err "No suitable deployment environment detected"
      return 1
    fi
  fi

  return 0
}

##############################################################################
# Dependency Installation
##############################################################################

install_dependencies() {
  if [ "$SKIP_DEPS" = true ]; then
    log_info "Skipping dependency installation"
    return 0
  fi

  log_section "Installing Dependencies"

  cd "$PROJECT_ROOT"

  # Create virtual environment if needed
  if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    log_step "Creating virtual environment"

    if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
      log_err "Python not found. Please install Python 3.11+"
      return 1
    fi

    # Use python3 if available, otherwise python
    if command -v python3 >/dev/null 2>&1; then
      python3 -m venv .venv
    else
      python -m venv .venv
    fi

    log_ok "Virtual environment created"
  fi

  # Activate virtual environment
  log_step "Activating virtual environment"
  if [ -f ".venv/Scripts/activate" ]; then
    source ".venv/Scripts/activate"
  elif [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
  elif [ -f "venv/Scripts/activate" ]; then
    source "venv/Scripts/activate"
  elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
  else
    log_err "Could not find virtual environment activation script"
    return 1
  fi

  log_ok "Virtual environment activated"

  # Upgrade pip
  log_step "Upgrading pip and build tools"
  python -m pip install --quiet --upgrade pip setuptools wheel
  log_ok "pip upgraded"

  # Install dependencies
  log_step "Installing Python dependencies"

  if [ -f "requirements-dev.txt" ]; then
    log_info "Installing requirements-dev.txt..."
    python -m pip install --quiet -r requirements-dev.txt || true
  fi

  if [ -f "backend/requirements.txt" ]; then
    log_info "Installing backend requirements..."
    python -m pip install --quiet -r backend/requirements.txt || true
  fi

  if [ -f "backend/requirements-dev.txt" ]; then
    log_info "Installing backend dev requirements..."
    python -m pip install --quiet -r backend/requirements-dev.txt || true
  fi

  log_ok "Dependencies installed"
}

##############################################################################
# Pre-flight Validation
##############################################################################

run_preflight_checks() {
  log_section "Running Pre-flight Checks"

  if [ ! -f "$SCRIPT_DIR/preflight-env.sh" ]; then
    log_err "Preflight validation script not found"
    return 1
  fi

  if bash "$SCRIPT_DIR/preflight-env.sh" >/dev/null 2>&1; then
    log_ok "Preflight checks passed"
  else
    log_info "Preflight checks failed (non-critical, continuing)"
    log_info "Run 'bash scripts/preflight-env.sh' for details"
  fi

  return 0
}

##############################################################################
# Docker Installation
##############################################################################

install_docker_mode() {
  log_section "Docker Installation"

  # Check Docker Compose
  if docker compose version >/dev/null 2>&1; then
    log_ok "Docker Compose v2 available"
  elif docker-compose version >/dev/null 2>&1; then
    log_ok "Docker Compose standalone available"
  else
    log_err "Docker Compose not found"
    return 1
  fi

  # Check docker-compose.yml
  if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    log_err "docker-compose.yml not found"
    return 1
  fi

  log_ok "Docker installation ready"
  log_info "To deploy, run: bash scripts/deploy-unified.sh --docker"
}

##############################################################################
# Bare-metal Installation
##############################################################################

install_bare_metal_mode() {
  log_section "Bare-metal Installation"

  # Check systemd
  if ! command -v systemctl >/dev/null 2>&1; then
    log_err "systemd not found"
    return 1
  fi

  log_ok "systemd available"

  # Check for systemd service files
  if compgen -G "$PROJECT_ROOT/config/systemd/*.service" >/dev/null; then
    log_ok "Systemd service files found"
  else
    log_info "No systemd service files found (optional)"
  fi

  log_ok "Bare-metal installation ready"
  log_info "To deploy, run: bash scripts/deploy-unified.sh --bare-metal"
}

##############################################################################
# Help
##############################################################################

show_help() {
  cat <<EOF
Installation Wizard - One-command setup for deployment automation

Usage:
  bash scripts/install.sh [OPTIONS]

Options:
  --check              Check if installation is complete
  --docker             Force Docker installation
  --bare-metal         Force bare-metal (systemd) installation
  --skip-deps          Skip dependency installation
  --help, -h           Show this help

Examples:
  # Interactive installation (auto-detects environment)
  bash scripts/install.sh

  # Check installation status
  bash scripts/install.sh --check

  # Force Docker installation
  bash scripts/install.sh --docker

  # Skip dependency installation (faster)
  bash scripts/install.sh --skip-deps

EOF
}

##############################################################################
# Main
##############################################################################

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --check)
        CHECK_ONLY=true
        shift
        ;;
      --docker)
        INSTALL_MODE="docker"
        shift
        ;;
      --bare-metal)
        INSTALL_MODE="bare-metal"
        shift
        ;;
      --skip-deps)
        SKIP_DEPS=true
        shift
        ;;
      --help|-h)
        show_help
        exit 0
        ;;
      *)
        log_err "Unknown option: $1"
        show_help
        exit 1
        ;;
    esac
  done

  # Check mode
  if [ "$CHECK_ONLY" = true ]; then
    check_installation
    exit $?
  fi

  # Welcome message
  log_section "Installation Wizard"
  echo ""
  echo "This wizard will guide you through the installation process."
  echo "It will detect your environment and install necessary dependencies."
  echo ""

  # Detect environment
  if ! detect_environment; then
    log_err "Environment detection failed"
    log_info "Please install Python 3.11+ and/or Docker to continue"
    exit 1
  fi

  # Install dependencies
  if ! install_dependencies; then
    log_err "Dependency installation failed"
    exit 1
  fi

  # Run pre-flight checks
  run_preflight_checks

  # Mode-specific installation
  case "$INSTALL_MODE" in
    docker)
      install_docker_mode
      ;;
    bare-metal)
      install_bare_metal_mode
      ;;
    *)
      log_err "Unknown installation mode: $INSTALL_MODE"
      exit 1
      ;;
  esac

  # Completion message
  log_section "Installation Complete"
  echo ""
  log_ok "Installation completed successfully"
  echo ""
  log_info "Next steps:"
  if [ "$INSTALL_MODE" = "docker" ]; then
    echo "  1. Configure your environment (.env file)"
    echo "  2. Run: bash scripts/deploy-unified.sh --docker"
  else
    echo "  1. Configure your environment (.env file)"
    echo "  2. Run: bash scripts/deploy-unified.sh --bare-metal"
  fi
  echo ""
  log_info "For troubleshooting, see: docs/deployment/TROUBLESHOOTING.md"
  echo ""
}

main "$@"
