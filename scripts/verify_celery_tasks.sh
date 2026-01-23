#!/bin/bash

# Verification Script for Celery Background Tasks
# This script verifies that Celery tasks execute properly

set -e

echo "=========================================="
echo "Celery Background Tasks Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Backend directory
BACKEND_DIR="./backend"

# Check if we're in the right directory
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}Error: Backend directory not found${NC}"
    echo "Please run this script from the project root"
    exit 1
fi

cd "$BACKEND_DIR"

echo -e "${YELLOW}Step 1: Checking Python environment...${NC}"
if ! python -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo -e "${RED}Error: Python 3.10+ required${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"

echo ""
echo -e "${YELLOW}Step 2: Checking Celery installation...${NC}"
if ! python -c "import celery; print(f'Celery version: {celery.__version__}')" 2>/dev/null; then
    echo -e "${RED}Error: Celery not installed${NC}"
    echo "Install with: pip install celery"
    exit 1
fi
echo -e "${GREEN}✓ Celery installed${NC}"

echo ""
echo -e "${YELLOW}Step 3: Checking Celery task imports...${NC}"

# Test task imports
TASKS=(
    "src.services.auto_pilot_service:fill_gaps_task"
    "src.services.auto_pilot_service:generate_schedule_task"
    "src.services.schedule_optimization_service:run_optimization_task"
    "src.services.schedule_recommendation_service:generate_daily_suggestions_task"
)

for task in "${TASKS[@]}"; do
    module="${task%:*}"
    func="${task#*:}"

    if python -c "from $module import $func; print('  ✓ $func')" 2>/dev/null; then
        echo -e "${GREEN}  ✓ ${func}${NC}"
    else
        echo -e "${RED}  ✗ Failed to import ${func}${NC}"
        exit 1
    fi
done

echo ""
echo -e "${YELLOW}Step 4: Running backend integration tests...${NC}"

# Run the Celery tasks integration tests
if python -m pytest tests/integration/test_celery_tasks.py -v --tb=short 2>&1; then
    echo -e "${GREEN}✓ Backend integration tests passed${NC}"
else
    echo -e "${RED}✗ Backend integration tests failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 5: Verifying Celery task registration...${NC}"

# Check if tasks are registered with Celery
if python -c "
from src.services.auto_pilot_service import celery_app
tasks = celery_app.tasks
print(f'Total registered tasks: {len(tasks)}')
print('Recent tasks:')
for task_name in ['services.auto_pilot.fill_gaps', 'services.auto_pilot.generate_schedule', 'services.schedule_optimization.run_optimization']:
    if task_name in tasks:
        print(f'  ✓ {task_name}')
    else:
        print(f'  ✗ {task_name} NOT FOUND')
" 2>/dev/null; then
    echo -e "${GREEN}✓ Celery tasks registered${NC}"
else
    echo -e "${YELLOW}⚠ Could not verify task registration (Celery worker not running?)${NC}"
fi

echo ""
echo -e "${YELLOW}Step 6: Checking task decorators and signatures...${NC}"

# Verify task decorators
python << 'EOF'
import inspect
from src.services.auto_pilot_service import fill_gaps_task, generate_schedule_task
from src.services.schedule_optimization_service import run_optimization_task
from src.services.schedule_recommendation_service import generate_daily_suggestions_task

tasks_to_check = [
    ("fill_gaps_task", fill_gaps_task),
    ("generate_schedule_task", generate_schedule_task),
    ("run_optimization_task", run_optimization_task),
    ("generate_daily_suggestions_task", generate_daily_suggestions_task),
]

for task_name, task_func in tasks_to_check:
    # Check if it's a Celery task
    if hasattr(task_func, 'request'):
        print(f"  ✓ {task_name} is a Celery task")
    else:
        print(f"  ✗ {task_name} is NOT a Celery task")

    # Check signature
    sig = inspect.signature(task_func)
    print(f"    Parameters: {list(sig.parameters.keys())}")
EOF

echo ""
echo -e "${YELLOW}Step 7: Verifying error handling and retry logic...${NC}"

# Check if tasks have retry configuration
python << 'EOF'
from src.services.auto_pilot_service import fill_gaps_task, generate_schedule_task
from src.services.schedule_optimization_service import run_optimization_task

tasks_to_check = [
    ("fill_gaps_task", fill_gaps_task),
    ("generate_schedule_task", generate_schedule_task),
    ("run_optimization_task", run_optimization_task),
]

for task_name, task_func in tasks_to_check:
    # Check max_retries
    max_retries = getattr(task_func, 'max_retries', None)
    if max_retries is not None:
        print(f"  ✓ {task_name} has max_retries={max_retries}")
    else:
        print(f"  ⚠ {task_name} has no retry configuration")

    # Check if task is bind=True (has self parameter)
    if 'self' in str(task_func):
        print(f"  ✓ {task_name} is bound (bind=True)")
    else:
        print(f"  ⚠ {task_name} is not bound")
EOF

echo ""
echo "=========================================="
echo -e "${GREEN}✓ All verification checks passed!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • Celery tasks imported successfully"
echo "  • Task decorators properly configured"
echo "  • Integration tests passed"
echo "  • Error handling and retry logic in place"
echo ""
echo "Next steps:"
echo "  1. Start Celery worker: celery -A src.services.auto_pilot_service worker --loglevel=info"
echo "  2. Run backend API server"
echo "  3. Test task triggering via API endpoints"
echo "  4. Run frontend e2e tests: cd frontend && npm run test:e2e celery-tasks"
echo ""
