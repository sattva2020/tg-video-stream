"""
Pydantic схемы для API инцидентов.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    """Уровни логов."""
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"


class LogType(str, Enum):
    """Типы логов."""
    CONSOLE = "console"
    NETWORK = "network"
    ACTION = "action"
    PERFORMANCE = "performance"


class IncidentStatusEnum(str, Enum):
    """Статусы инцидентов."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"
    DUPLICATE = "duplicate"


class IncidentPriorityEnum(str, Enum):
    """Приоритеты инцидентов."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCategoryEnum(str, Enum):
    """Категории инцидентов."""
    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"
    PERFORMANCE = "performance"
    SECURITY = "security"
    UI_UX = "ui_ux"
    OTHER = "other"


# === Логи ===

class BrowserInfo(BaseModel):
    """Информация о браузере."""
    name: str
    version: str
    os: str
    platform: str
    userAgent: str
    language: str
    screenResolution: str
    viewportSize: str
    colorDepth: int
    timezone: str


class ConsoleLogEntry(BaseModel):
    """Лог консоли."""
    type: str = "console"
    level: LogLevel
    message: str
    stack: Optional[str] = None
    timestamp: str
    metadata: Optional[dict] = None


class NetworkLogEntry(BaseModel):
    """Лог сетевого запроса."""
    type: str = "network"
    url: str
    method: str
    statusCode: Optional[int] = None
    responseTimeMs: Optional[int] = None
    error: Optional[str] = None
    timestamp: str
    metadata: Optional[dict] = None


class ActionLogEntry(BaseModel):
    """Лог действия пользователя."""
    type: str = "action"
    action: str
    element: Optional[str] = None
    value: Optional[str] = None
    timestamp: str
    metadata: Optional[dict] = None


class PerformanceLogEntry(BaseModel):
    """Лог производительности."""
    type: str = "performance"
    metric: str
    value: float
    timestamp: str
    metadata: Optional[dict] = None


# === Инциденты ===

class CreateIncidentRequest(BaseModel):
    """Запрос на создание инцидента."""
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10, max_length=10000)
    logs: List[dict] = Field(default_factory=list)
    browserInfo: BrowserInfo
    pageUrl: str
    screenshot: Optional[str] = None  # Base64
    tags: Optional[List[str]] = None


class SimilarIncidentResponse(BaseModel):
    """Похожий инцидент."""
    id: str
    title: str
    status: IncidentStatusEnum
    similarity: float = Field(..., ge=0.0, le=1.0)
    solution: Optional[str] = None


class CreateIncidentResponse(BaseModel):
    """Ответ на создание инцидента."""
    id: str
    title: str
    status: IncidentStatusEnum
    priority: IncidentPriorityEnum
    category: Optional[IncidentCategoryEnum] = None
    aiSuggestedSolution: Optional[str] = None
    similarIncidents: List[SimilarIncidentResponse] = []
    createdAt: datetime

    class Config:
        from_attributes = True


class AttachmentResponse(BaseModel):
    """Вложение."""
    filename: str
    url: str
    mimeType: str
    size: int


class CommentResponse(BaseModel):
    """Комментарий к инциденту."""
    id: str
    incidentId: str
    userId: Optional[str] = None
    userName: Optional[str] = None
    content: str
    isInternal: bool
    isAiGenerated: bool
    attachments: List[AttachmentResponse] = []
    createdAt: datetime

    class Config:
        from_attributes = True


class IncidentResponse(BaseModel):
    """Полная модель инцидента."""
    id: str
    userId: Optional[str] = None
    title: str
    description: str
    status: IncidentStatusEnum
    priority: IncidentPriorityEnum
    category: Optional[IncidentCategoryEnum] = None
    browserInfo: Optional[dict] = None
    pageUrl: Optional[str] = None
    aiAnalysis: Optional[dict] = None
    aiSuggestedSolution: Optional[str] = None
    aiConfidence: Optional[float] = None
    similarIncidentId: Optional[str] = None
    tags: List[str] = []
    assignedToId: Optional[str] = None
    assignedToName: Optional[str] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    resolvedAt: Optional[datetime] = None
    comments: List[CommentResponse] = []
    logsCount: int = 0

    class Config:
        from_attributes = True


class IncidentListItem(BaseModel):
    """Краткая модель инцидента для списка."""
    id: str
    title: str
    status: IncidentStatusEnum
    priority: IncidentPriorityEnum
    category: Optional[IncidentCategoryEnum] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    assignedToName: Optional[str] = None
    logsCount: int = 0
    commentsCount: int = 0

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    """Список инцидентов с пагинацией."""
    items: List[IncidentListItem]
    total: int
    page: int
    pageSize: int
    totalPages: int


class UpdateIncidentRequest(BaseModel):
    """Запрос на обновление инцидента."""
    status: Optional[IncidentStatusEnum] = None
    priority: Optional[IncidentPriorityEnum] = None
    category: Optional[IncidentCategoryEnum] = None
    assignedToId: Optional[str] = None
    tags: Optional[List[str]] = None


class AddCommentRequest(BaseModel):
    """Запрос на добавление комментария."""
    content: str = Field(..., min_length=1, max_length=5000)
    isInternal: bool = False


class SolutionResponse(BaseModel):
    """Решение из базы знаний."""
    id: str
    problemTitle: str
    problemDescription: str
    solution: str
    category: Optional[IncidentCategoryEnum] = None
    keywords: List[str] = []
    timesUsed: int
    positiveFeedback: int
    negativeFeedback: int
    createdAt: datetime

    class Config:
        from_attributes = True


class CreateSolutionRequest(BaseModel):
    """Запрос на создание решения."""
    sourceIncidentId: Optional[str] = None
    problemTitle: str = Field(..., min_length=5, max_length=500)
    problemDescription: str = Field(..., min_length=10, max_length=5000)
    solution: str = Field(..., min_length=10, max_length=10000)
    category: Optional[IncidentCategoryEnum] = None
    keywords: Optional[List[str]] = None


class SolutionFeedbackRequest(BaseModel):
    """Запрос на фидбек по решению."""
    isPositive: bool
