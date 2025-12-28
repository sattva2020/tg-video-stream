#!/bin/bash
# Backend Coverage Runner
# Запускает тесты 8 приоритетных сервисов с coverage отчётом

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         Backend Coverage - Priority Services             ║"
echo "║              Target: 98.75% Coverage                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if we're in backend directory
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}Error: Not in backend directory. Run this script from backend/${NC}"
    exit 1
fi

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo "Attempting to activate..."
    if [ -f "../venv/bin/activate" ]; then
        source ../venv/bin/activate
    elif [ -f "../venv/Scripts/activate" ]; then
        source ../venv/Scripts/activate
    else
        echo -e "${RED}Error: Virtual environment not found${NC}"
        exit 1
    fi
fi

# Run tests
echo -e "${BLUE}Running tests for 8 priority services...${NC}"
echo ""

python -m pytest \
  tests/test_playback_service.py \
  tests/test_auth_service.py \
  tests/test_session_service.py \
  tests/test_activity_service.py \
  tests/test_telegram_rate_limiter.py \
  tests/test_queue_service.py \
  tests/test_priority_queue_service.py \
  tests/test_channel_service.py \
  --cov=src.services.playback_service \
  --cov=src.services.auth_service \
  --cov=src.services.session_service \
  --cov=src.services.activity_service \
  --cov=src.services.telegram_rate_limiter \
  --cov=src.services.queue_service \
  --cov=src.services.priority_queue_service \
  --cov=src.services.channel_service \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=json \
  --cov-branch \
  -v

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    
    # Parse coverage
    if [ -f "coverage.json" ]; then
        echo ""
        echo -e "${BLUE}📊 Coverage Summary:${NC}"
        python3 scripts/parse_coverage.py
    fi
    
    # Open HTML report
    echo ""
    echo -e "${BLUE}📄 HTML report generated: htmlcov/index.html${NC}"
    
    # Try to open in browser (cross-platform)
    if command -v xdg-open > /dev/null; then
        echo "Opening in browser..."
        xdg-open htmlcov/index.html
    elif command -v open > /dev/null; then
        echo "Opening in browser..."
        open htmlcov/index.html
    elif command -v start > /dev/null; then
        echo "Opening in browser..."
        start htmlcov/index.html
    else
        echo -e "${YELLOW}Open htmlcov/index.html manually in your browser${NC}"
    fi
    
else
    echo ""
    echo -e "${RED}❌ Tests failed${NC}"
    exit 1
fi
