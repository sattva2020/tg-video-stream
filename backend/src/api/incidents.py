"""
API endpoints для системы инцидентов и поддержки.

Endpoints:
- POST /incidents - создание инцидента
- GET /incidents - список инцидентов (для админов)
- GET /incidents/{id} - получение инцидента
- PATCH /incidents/{id} - обновление инцидента
- POST /incidents/{id}/comments - добавление комментария
- GET /incidents/{id}/logs - получение логов инцидента
- GET /incidents/similar - поиск похожих инцидентов
- GET /solutions - база знаний решений
- POST /solutions - создание решения
- POST /solutions/{id}/feedback - фидбек по решению
"""
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import Base
from src.lib.db import get_db
from src.api.auth.dependencies import get_current_user
from src.lib.rbac import require_role
from src.models.user import User
from src.models.incident import (
    Incident, IncidentLog, IncidentComment, IncidentSolution, IncidentEmbedding,
    IncidentStatus, IncidentPriority, IncidentCategory
)
from src.schemas.incident import (
    CreateIncidentRequest, CreateIncidentResponse, IncidentResponse,
    IncidentListResponse, IncidentListItem, UpdateIncidentRequest,
    AddCommentRequest, CommentResponse, SimilarIncidentResponse,
    SolutionResponse, CreateSolutionRequest, SolutionFeedbackRequest,
    IncidentStatusEnum, IncidentPriorityEnum, IncidentCategoryEnum
)

router = APIRouter(prefix="/incidents", tags=["incidents"])
solutions_router = APIRouter(prefix="/solutions", tags=["solutions"])


# === Вспомогательные функции ===

def parse_log_entries(logs_data: List[dict]) -> List[IncidentLog]:
    """Парсинг логов из запроса в модели."""
    result = []
    for log in logs_data:
        log_type = log.get("type", "console")
        timestamp_str = log.get("timestamp", datetime.now(timezone.utc).isoformat())
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.now(timezone.utc)
        
        incident_log = IncidentLog(
            log_type=log_type,
            level=log.get("level"),
            message=log.get("message"),
            stack_trace=log.get("stack"),
            url=log.get("url"),
            method=log.get("method"),
            status_code=log.get("statusCode"),
            response_time_ms=log.get("responseTimeMs"),
            action=log.get("action"),
            element=log.get("element"),
            metadata=log.get("metadata"),
            timestamp=timestamp
        )
        result.append(incident_log)
    
    return result


async def analyze_incident_with_ai(
    incident: Incident,
    db: AsyncSession
) -> dict:
    """
    Анализ инцидента с помощью AI.
    
    Использует IncidentAnalyzer для:
    - Классификации категории и приоритета
    - Поиска похожих решённых инцидентов
    - Генерации предложенного решения
    
    Получает API ключи из app_settings (БД) с fallback на .env.
    """
    from src.services.incident_analyzer import get_incident_analyzer_async
    
    try:
        # Получаем анализатор с ключами из БД/env
        analyzer = await get_incident_analyzer_async(db)
        
        # Полный анализ инцидента
        analysis = await analyzer.analyze_incident(incident)
        
        await analyzer.close()
        
        return {
            "category": analysis.get("category", IncidentCategory.OTHER),
            "priority": analysis.get("priority", IncidentPriority.MEDIUM),
            "suggested_solution": analysis.get("suggested_solution"),
            "confidence": analysis.get("confidence", 0.5),
            "similar_incidents": analysis.get("similar_incidents", [])
        }
        
    except Exception as e:
        print(f"AI analysis failed, using keyword fallback: {e}")
        # Fallback на keyword-based анализ
        return await _keyword_based_analysis(incident, db)


async def _keyword_based_analysis(incident: Incident, db: AsyncSession) -> dict:
    """Fallback анализ на основе ключевых слов (когда AI недоступен)."""
    title_lower = incident.title.lower()
    description_lower = incident.description.lower()
    combined = f"{title_lower} {description_lower}"
    
    # Определение категории по ключевым словам
    category = IncidentCategory.OTHER
    if any(word in combined for word in ["ошибка", "error", "баг", "bug", "не работает", "сломал"]):
        category = IncidentCategory.BUG
    elif any(word in combined for word in ["медленно", "тормоз", "долго", "slow", "performance"]):
        category = IncidentCategory.PERFORMANCE
    elif any(word in combined for word in ["хочу", "добавить", "функция", "feature", "можно ли"]):
        category = IncidentCategory.FEATURE_REQUEST
    elif any(word in combined for word in ["как", "почему", "зачем", "what", "how", "why"]):
        category = IncidentCategory.QUESTION
    elif any(word in combined for word in ["интерфейс", "ui", "ux", "дизайн", "кнопка", "меню"]):
        category = IncidentCategory.UI_UX
    elif any(word in combined for word in ["безопасность", "пароль", "доступ", "security"]):
        category = IncidentCategory.SECURITY
    
    # Определение приоритета
    priority = IncidentPriority.MEDIUM
    error_count = sum(1 for log in incident.logs if log.level == "error")
    
    if error_count > 5 or any(word in combined for word in ["критично", "urgent", "срочно", "не могу войти"]):
        priority = IncidentPriority.CRITICAL
    elif error_count > 2 or any(word in combined for word in ["важно", "блокирует"]):
        priority = IncidentPriority.HIGH
    elif any(word in combined for word in ["мелочь", "хотелось бы", "было бы неплохо"]):
        priority = IncidentPriority.LOW
    
    # Поиск похожих решений
    similar_incidents = []
    solutions_query = select(IncidentSolution).where(
        IncidentSolution.is_active == True
    ).limit(5)
    
    solutions_result = await db.execute(solutions_query)
    solutions = solutions_result.scalars().all()
    
    # Простой поиск по ключевым словам
    for solution in solutions:
        solution_text = f"{solution.problem_title} {solution.problem_description}".lower()
        
        # Считаем совпадающие слова
        title_words = set(title_lower.split())
        solution_words = set(solution_text.split())
        common_words = title_words & solution_words
        
        if len(common_words) >= 2:
            similarity = len(common_words) / max(len(title_words), 1)
            similar_incidents.append({
                "id": str(solution.source_incident_id) if solution.source_incident_id else str(solution.id),
                "title": solution.problem_title,
                "solution": solution.solution,
                "similarity": min(similarity, 0.95)
            })
    
    # Сортируем по схожести
    similar_incidents.sort(key=lambda x: x["similarity"], reverse=True)
    similar_incidents = similar_incidents[:3]  # Топ 3
    
    # Предложенное решение
    suggested_solution = None
    if similar_incidents and similar_incidents[0]["similarity"] > 0.5:
        suggested_solution = similar_incidents[0]["solution"]
    
    return {
        "category": category,
        "priority": priority,
        "suggested_solution": suggested_solution,
        "confidence": 0.4,  # Низкая уверенность для keyword-based
        "similar_incidents": similar_incidents
    }


# === Endpoints ===

@router.post("", response_model=CreateIncidentResponse)
async def create_incident(
    request: CreateIncidentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Создание нового инцидента.
    
    Автоматически:
    - Анализирует проблему с помощью AI
    - Определяет категорию и приоритет
    - Ищет похожие решённые инциденты
    - Предлагает решение, если найдено
    """
    # Создаём инцидент
    incident = Incident(
        user_id=current_user.id if current_user else None,
        title=request.title,
        description=request.description,
        status=IncidentStatus.NEW,
        priority=IncidentPriority.MEDIUM,
        browser_info=request.browserInfo.model_dump(),
        page_url=request.pageUrl,
        tags=request.tags or []
    )
    
    # Парсим и добавляем логи
    logs = parse_log_entries(request.logs)
    for log in logs:
        log.incident = incident
    
    db.add(incident)
    db.add_all(logs)
    
    # Сохраняем скриншот как первый комментарий (если есть)
    if request.screenshot:
        screenshot_comment = IncidentComment(
            incident=incident,
            user_id=current_user.id if current_user else None,
            content="📷 Скриншот прикреплён",
            attachments=[{
                "filename": "screenshot.png",
                "url": request.screenshot,  # В продакшене сохранять в S3/MinIO
                "mimeType": "image/png",
                "size": len(request.screenshot)
            }]
        )
        db.add(screenshot_comment)
    
    await db.commit()
    await db.refresh(incident, ["logs"])
    
    # AI анализ
    ai_result = await analyze_incident_with_ai(incident, db)
    
    # Обновляем инцидент с результатами AI
    incident.category = ai_result["category"]
    incident.priority = ai_result["priority"]
    incident.ai_suggested_solution = ai_result["suggested_solution"]
    incident.ai_confidence = ai_result["confidence"]
    incident.ai_analysis = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "method": "keyword_matching",  # TODO: заменить на "ai_model" когда подключим
    }
    
    await db.commit()
    
    # Формируем ответ
    similar_incidents = [
        SimilarIncidentResponse(
            id=s["id"],
            title=s["title"],
            status=IncidentStatusEnum.RESOLVED,
            similarity=s["similarity"],
            solution=s["solution"]
        )
        for s in ai_result["similar_incidents"]
    ]
    
    return CreateIncidentResponse(
        id=str(incident.id),
        title=incident.title,
        status=IncidentStatusEnum(incident.status.value),
        priority=IncidentPriorityEnum(incident.priority.value),
        category=IncidentCategoryEnum(incident.category.value) if incident.category else None,
        aiSuggestedSolution=incident.ai_suggested_solution,
        similarIncidents=similar_incidents,
        createdAt=incident.created_at
    )


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    status: Optional[IncidentStatusEnum] = None,
    priority: Optional[IncidentPriorityEnum] = None,
    category: Optional[IncidentCategoryEnum] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin", "moderator"]))
):
    """
    Получение списка инцидентов (для админов).
    """
    query = select(Incident)
    
    # Фильтры
    if status:
        query = query.where(Incident.status == IncidentStatus(status.value))
    if priority:
        query = query.where(Incident.priority == IncidentPriority(priority.value))
    if category:
        query = query.where(Incident.category == IncidentCategory(category.value))
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Incident.title.ilike(search_pattern),
                Incident.description.ilike(search_pattern)
            )
        )
    
    # Подсчёт общего количества
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Пагинация и сортировка
    query = query.order_by(desc(Incident.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.options(selectinload(Incident.assigned_to))
    
    result = await db.execute(query)
    incidents = result.scalars().all()
    
    # Формируем ответ
    items = []
    for incident in incidents:
        # Подсчёт логов и комментариев
        logs_count = await db.scalar(
            select(func.count()).where(IncidentLog.incident_id == incident.id)
        ) or 0
        comments_count = await db.scalar(
            select(func.count()).where(IncidentComment.incident_id == incident.id)
        ) or 0
        
        items.append(IncidentListItem(
            id=str(incident.id),
            title=incident.title,
            status=IncidentStatusEnum(incident.status.value),
            priority=IncidentPriorityEnum(incident.priority.value),
            category=IncidentCategoryEnum(incident.category.value) if incident.category else None,
            createdAt=incident.created_at,
            updatedAt=incident.updated_at,
            assignedToName=incident.assigned_to.full_name if incident.assigned_to else None,
            logsCount=logs_count,
            commentsCount=comments_count
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return IncidentListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages
    )


@router.get("/my", response_model=IncidentListResponse)
async def list_my_incidents(
    status: Optional[IncidentStatusEnum] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка своих инцидентов.
    """
    query = select(Incident).where(Incident.user_id == current_user.id)
    
    if status:
        query = query.where(Incident.status == IncidentStatus(status.value))
    
    # Подсчёт
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Пагинация
    query = query.order_by(desc(Incident.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    incidents = result.scalars().all()
    
    items = []
    for incident in incidents:
        logs_count = await db.scalar(
            select(func.count()).where(IncidentLog.incident_id == incident.id)
        ) or 0
        comments_count = await db.scalar(
            select(func.count()).where(IncidentComment.incident_id == incident.id)
        ) or 0
        
        items.append(IncidentListItem(
            id=str(incident.id),
            title=incident.title,
            status=IncidentStatusEnum(incident.status.value),
            priority=IncidentPriorityEnum(incident.priority.value),
            category=IncidentCategoryEnum(incident.category.value) if incident.category else None,
            createdAt=incident.created_at,
            updatedAt=incident.updated_at,
            logsCount=logs_count,
            commentsCount=comments_count
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return IncidentListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение инцидента по ID.
    """
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID")
    
    query = select(Incident).where(Incident.id == incident_uuid)
    query = query.options(
        selectinload(Incident.assigned_to),
        selectinload(Incident.comments).selectinload(IncidentComment.user)
    )
    
    result = await db.execute(query)
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Проверка доступа
    is_admin = current_user.role in ["admin", "superadmin", "moderator"]
    if not is_admin and incident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Подсчёт логов
    logs_count = await db.scalar(
        select(func.count()).where(IncidentLog.incident_id == incident.id)
    ) or 0
    
    # Фильтруем внутренние комментарии для обычных пользователей
    comments = []
    for comment in incident.comments:
        if comment.is_internal and not is_admin:
            continue
        comments.append(CommentResponse(
            id=str(comment.id),
            incidentId=str(comment.incident_id),
            userId=str(comment.user_id) if comment.user_id else None,
            userName=comment.user.full_name if comment.user else None,
            content=comment.content,
            isInternal=comment.is_internal,
            isAiGenerated=comment.is_ai_generated,
            attachments=comment.attachments or [],
            createdAt=comment.created_at
        ))
    
    return IncidentResponse(
        id=str(incident.id),
        userId=str(incident.user_id) if incident.user_id else None,
        title=incident.title,
        description=incident.description,
        status=IncidentStatusEnum(incident.status.value),
        priority=IncidentPriorityEnum(incident.priority.value),
        category=IncidentCategoryEnum(incident.category.value) if incident.category else None,
        browserInfo=incident.browser_info,
        pageUrl=incident.page_url,
        aiAnalysis=incident.ai_analysis,
        aiSuggestedSolution=incident.ai_suggested_solution,
        aiConfidence=incident.ai_confidence,
        similarIncidentId=str(incident.similar_incident_id) if incident.similar_incident_id else None,
        tags=incident.tags or [],
        assignedToId=str(incident.assigned_to_id) if incident.assigned_to_id else None,
        assignedToName=incident.assigned_to.full_name if incident.assigned_to else None,
        createdAt=incident.created_at,
        updatedAt=incident.updated_at,
        resolvedAt=incident.resolved_at,
        comments=comments,
        logsCount=logs_count
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    request: UpdateIncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin", "moderator"]))
):
    """
    Обновление инцидента (для админов).
    """
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID")
    
    result = await db.execute(select(Incident).where(Incident.id == incident_uuid))
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Обновляем поля
    if request.status:
        incident.status = IncidentStatus(request.status.value)
        if request.status == IncidentStatusEnum.RESOLVED:
            incident.resolved_at = datetime.now(timezone.utc)
    if request.priority:
        incident.priority = IncidentPriority(request.priority.value)
    if request.category:
        incident.category = IncidentCategory(request.category.value)
    if request.assignedToId:
        try:
            incident.assigned_to_id = uuid.UUID(request.assignedToId)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid assignedToId")
    if request.tags is not None:
        incident.tags = request.tags
    
    await db.commit()
    
    # Возвращаем обновлённый инцидент
    return await get_incident(incident_id, db, current_user)


@router.post("/{incident_id}/comments", response_model=CommentResponse)
async def add_comment(
    incident_id: str,
    request: AddCommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавление комментария к инциденту.
    """
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID")
    
    result = await db.execute(select(Incident).where(Incident.id == incident_uuid))
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Проверка доступа
    is_admin = current_user.role in ["admin", "superadmin", "moderator"]
    if not is_admin and incident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Внутренние комментарии могут добавлять только админы
    if request.isInternal and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can add internal comments")
    
    comment = IncidentComment(
        incident_id=incident_uuid,
        user_id=current_user.id,
        content=request.content,
        is_internal=request.isInternal
    )
    
    db.add(comment)
    
    # Обновляем статус на "ожидает ответа" если это ответ поддержки
    if is_admin and incident.status == IncidentStatus.IN_PROGRESS:
        incident.status = IncidentStatus.WAITING_USER
    elif not is_admin and incident.status == IncidentStatus.WAITING_USER:
        incident.status = IncidentStatus.IN_PROGRESS
    
    await db.commit()
    await db.refresh(comment, ["user"])
    
    return CommentResponse(
        id=str(comment.id),
        incidentId=str(comment.incident_id),
        userId=str(comment.user_id),
        userName=current_user.full_name,
        content=comment.content,
        isInternal=comment.is_internal,
        isAiGenerated=False,
        attachments=[],
        createdAt=comment.created_at
    )


@router.get("/{incident_id}/logs")
async def get_incident_logs(
    incident_id: str,
    log_type: Optional[str] = None,
    level: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin", "moderator"]))
):
    """
    Получение логов инцидента (для админов).
    """
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID")
    
    query = select(IncidentLog).where(IncidentLog.incident_id == incident_uuid)
    
    if log_type:
        query = query.where(IncidentLog.log_type == log_type)
    if level:
        query = query.where(IncidentLog.level == level)
    
    # Подсчёт
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Пагинация
    query = query.order_by(IncidentLog.timestamp)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(log.id),
                "type": log.log_type,
                "level": log.level,
                "message": log.message,
                "stackTrace": log.stack_trace,
                "url": log.url,
                "method": log.method,
                "statusCode": log.status_code,
                "responseTimeMs": log.response_time_ms,
                "action": log.action,
                "element": log.element,
                "metadata": log.extra_data,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "pageSize": page_size
    }


# === Solutions API ===

@solutions_router.get("", response_model=List[SolutionResponse])
async def list_solutions(
    category: Optional[IncidentCategoryEnum] = None,
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение базы знаний решений.
    """
    query = select(IncidentSolution).where(IncidentSolution.is_active == True)
    
    if category:
        query = query.where(IncidentSolution.category == IncidentCategory(category.value))
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                IncidentSolution.problem_title.ilike(search_pattern),
                IncidentSolution.problem_description.ilike(search_pattern),
                IncidentSolution.solution.ilike(search_pattern)
            )
        )
    
    query = query.order_by(desc(IncidentSolution.times_used)).limit(limit)
    
    result = await db.execute(query)
    solutions = result.scalars().all()
    
    return [
        SolutionResponse(
            id=str(s.id),
            problemTitle=s.problem_title,
            problemDescription=s.problem_description,
            solution=s.solution,
            category=IncidentCategoryEnum(s.category.value) if s.category else None,
            keywords=s.keywords or [],
            timesUsed=s.times_used,
            positiveFeedback=s.positive_feedback,
            negativeFeedback=s.negative_feedback,
            createdAt=s.created_at
        )
        for s in solutions
    ]


@solutions_router.post("", response_model=SolutionResponse)
async def create_solution(
    request: CreateSolutionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"]))
):
    """
    Создание решения в базе знаний.
    """
    source_incident_uuid = None
    if request.sourceIncidentId:
        try:
            source_incident_uuid = uuid.UUID(request.sourceIncidentId)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid sourceIncidentId")
    
    solution = IncidentSolution(
        source_incident_id=source_incident_uuid,
        problem_title=request.problemTitle,
        problem_description=request.problemDescription,
        solution=request.solution,
        category=IncidentCategory(request.category.value) if request.category else None,
        keywords=request.keywords or [],
        created_by_id=current_user.id
    )
    
    db.add(solution)
    await db.commit()
    await db.refresh(solution)
    
    return SolutionResponse(
        id=str(solution.id),
        problemTitle=solution.problem_title,
        problemDescription=solution.problem_description,
        solution=solution.solution,
        category=IncidentCategoryEnum(solution.category.value) if solution.category else None,
        keywords=solution.keywords or [],
        timesUsed=0,
        positiveFeedback=0,
        negativeFeedback=0,
        createdAt=solution.created_at
    )


@solutions_router.post("/{solution_id}/feedback")
async def solution_feedback(
    solution_id: str,
    request: SolutionFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавление фидбека по решению.
    """
    try:
        solution_uuid = uuid.UUID(solution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid solution ID")
    
    result = await db.execute(
        select(IncidentSolution).where(IncidentSolution.id == solution_uuid)
    )
    solution = result.scalar_one_or_none()
    
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    
    if request.isPositive:
        solution.positive_feedback += 1
    else:
        solution.negative_feedback += 1
    
    solution.times_used += 1
    
    await db.commit()
    
    return {"success": True, "message": "Feedback recorded"}
