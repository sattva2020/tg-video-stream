# Frameworks Layer

**Architecture Layer**: Frameworks (Delivery Mechanisms)  
**Dependencies**: Application ✅, Infrastructure ✅, Domain ✅  
**Purpose**: HTTP API, CLI, Background Tasks, UI

## 📋 Содержание

- **api/**: FastAPI роуты, endpoints, request/response models
- **cli/**: CLI команды (Click, Typer)
- **tasks/**: Celery tasks для background jobs
- **middleware/**: HTTP middleware (logging, auth, CORS)

## 🌐 API Layer (FastAPI)

Frameworks layer **вызывает Use Cases**, не содержит бизнес-логику:

```python
# backend/src/frameworks/api/v1/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from backend.src.application.use_cases.create_user import CreateUserUseCase
from backend.src.application.dto.user import CreateUserRequest, CreateUserResponse
from backend.src.frameworks.api.dependencies import get_user_repository

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    repository=Depends(get_user_repository)
):
    """
    Создать нового пользователя.
    
    **HTTP Codes**:
    - 201: User created successfully
    - 400: Validation error (invalid email format)
    - 409: Email already exists
    """
    # 1. Use Case execution
    use_case = CreateUserUseCase(repository)
    result = await use_case.execute(request.email)
    
    # 2. Result → HTTP mapping
    if result.is_failure:
        # Domain error → HTTP code
        if "Invalid email" in result.error:
            raise HTTPException(status_code=400, detail=result.error)
        if "already exists" in result.error:
            raise HTTPException(status_code=409, detail=result.error)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    # 3. Domain Entity → DTO → Pydantic response
    user = result.value
    return CreateUserResponse(
        user_id=str(user.id.value),
        email=user.email.value,
        created_at=user.created_at.isoformat()
    )
```

## 🔌 Dependency Injection (FR-020)

DI container **в Frameworks layer** (Infrastructure wiring):

```python
# backend/src/frameworks/api/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from backend.src.infrastructure.persistence.database import get_db_session

async def get_user_repository(
    session: AsyncSession = Depends(get_db_session)
) -> SqlAlchemyUserRepository:
    """FastAPI Dependency для инжекции repository."""
    return SqlAlchemyUserRepository(session)
```

**Manual Wiring** (research.md §TD6): Не используем DI frameworks (dependency-injector).

## 🛡️ Input Validation (NFR-010)

Pydantic models валидируют **HTTP requests** (не Domain):

```python
# backend/src/frameworks/api/schemas/user_schema.py
from pydantic import BaseModel, EmailStr

class CreateUserRequestSchema(BaseModel):
    email: EmailStr  # HTTP-уровень валидация
    
    class Config:
        json_schema_extra = {
            "example": {"email": "user@example.com"}
        }
```

**Domain validation** отдельно в Value Objects (FR-011).

## 📋 CLI Commands

CLI для administrative tasks:

```python
# backend/src/frameworks/cli/users.py
import asyncio
import click
from backend.src.application.use_cases.create_user import CreateUserUseCase
from backend.src.frameworks.api.dependencies import get_user_repository

@click.command()
@click.argument("email")
async def create_user_cli(email: str):
    """CLI команда: создать пользователя."""
    repository = await get_user_repository()  # DI из Frameworks
    use_case = CreateUserUseCase(repository)
    result = await use_case.execute(email)
    
    if result.is_success:
        click.echo(f"✅ User created: {result.value.id}")
    else:
        click.echo(f"❌ Error: {result.error}", err=True)

if __name__ == "__main__":
    asyncio.run(create_user_cli())
```

## 🔄 Background Tasks (Celery)

Celery tasks **вызывают Use Cases**:

```python
# backend/src/frameworks/tasks/user_tasks.py
from celery import Celery
from backend.src.application.use_cases.send_welcome_email import SendWelcomeEmailUseCase

celery_app = Celery("sattva")

@celery_app.task
def send_welcome_email_task(user_id: str):
    """Background task: отправить welcome email."""
    # DI setup
    repository = get_user_repository()
    email_gateway = get_email_gateway()
    
    # Use Case execution
    use_case = SendWelcomeEmailUseCase(repository, email_gateway)
    result = asyncio.run(use_case.execute(user_id))
    
    if result.is_failure:
        raise Exception(f"Failed to send email: {result.error}")
```

## ✅ Testing (FR-015)

- **E2E Tests**: HTTP requests → Use Cases → DB
- **API Tests**: FastAPI TestClient

```bash
# E2E тесты (с реальной БД)
pytest backend/tests/e2e/api/ -v

# API unit тесты (с моками Use Cases)
pytest backend/tests/unit/frameworks/api/ -v
```

### E2E Test Example
```python
from fastapi.testclient import TestClient
from backend.src.main import app

client = TestClient(app)

def test_create_user_e2e():
    response = client.post("/api/v1/users/", json={"email": "test@example.com"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "user_id" in data
```

## 🚫 Запрещённые Действия

Frameworks **НЕ ДОЛЖЕН** содержать:
- ❌ Бизнес-логику (она в Domain)
- ❌ Direct database queries (используй Application Use Cases)
- ❌ Domain entities в response models (используй DTO)

## 📚 Связанные Документы

- [Application Layer README](../application/README.md)
- [FastAPI Best Practices](../../specs/025-clean-architecture-rules/quickstart.md)
- [API Documentation](../../docs/api/)
