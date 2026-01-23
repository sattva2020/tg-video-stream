"""
Q&A API endpoints for viewer questions and answers.

Created for Feature 020 (Viewer Interaction & Engagement Features).
Provides REST API for submitting, listing, upvoting, and answering questions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
import uuid

from src.database import get_db
from src.models.user import User
from src.models.qa import Question, QuestionUpvote, QuestionStatus
from api.auth import get_current_user

router = APIRouter()


# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================

class QuestionCreate(BaseModel):
    """Модель для создания вопроса."""
    stream_id: uuid.UUID
    content: str
    author_name: Optional[str] = None


class QuestionResponse(BaseModel):
    """Модель ответа для вопроса."""
    id: uuid.UUID
    stream_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    telegram_user_id: Optional[int] = None
    author_name: Optional[str] = None
    content: str
    status: QuestionStatus
    is_pinned: bool
    upvote_count: int
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    is_filtered: bool
    filter_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionUpdate(BaseModel):
    """Модель для обновления вопроса (ответ, статус)."""
    answer: Optional[str] = None
    status: Optional[QuestionStatus] = None
    is_pinned: Optional[bool] = None


# =============================================================================
# Question Endpoints
# =============================================================================

@router.get("/questions", response_model=List[QuestionResponse])
def list_questions(
    stream_id: Optional[uuid.UUID] = None,
    status_filter: Optional[QuestionStatus] = None,
    is_pinned: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список вопросов.

    Args:
        stream_id: Фильтр по ID стрима (опционально)
        status_filter: Фильтр по статусу (опционально)
        is_pinned: Фильтр по закрепленным вопросам (опционально)
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        List[QuestionResponse]: Список вопросов
    """
    # Базовый запрос - вопросы из стримов пользователя
    query = db.query(Question).join(
        "stream"
    ).filter(
        # TODO: Add proper access control - for now return all questions
        # In production, filter by streams owned by user or accessible to user
        True
    )

    if stream_id:
        query = query.filter(Question.stream_id == stream_id)

    if status_filter:
        query = query.filter(Question.status == status_filter)

    if is_pinned is not None:
        query = query.filter(Question.is_pinned == is_pinned)

    # Сортировка: сначала закрепленные, потом по количеству upvotes, потом по дате
    questions = query.order_by(
        Question.is_pinned.desc(),
        Question.upvote_count.desc(),
        Question.created_at.desc()
    ).all()

    return questions


@router.post("/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question_in: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать новый вопрос.

    Args:
        question_in: Данные для создания вопроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        QuestionResponse: Созданный вопрос

    Raises:
        HTTPException: Если стрим не найден или контент пустой
    """
    from src.models.stream import Stream

    # Проверяем существование стрима
    stream = db.query(Stream).filter(Stream.id == question_in.stream_id).first()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )

    # Валидация контента
    if not question_in.content or not question_in.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question content cannot be empty"
        )

    # Создаем вопрос
    new_question = Question(
        stream_id=question_in.stream_id,
        author_id=current_user.id,
        telegram_user_id=current_user.telegram_id,
        author_name=question_in.author_name or current_user.username,
        content=question_in.content.strip(),
        status=QuestionStatus.PENDING,
        is_pinned=False,
        upvote_count=0,
        is_filtered=False
    )

    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return new_question


@router.get("/questions/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить вопрос по ID.

    Args:
        question_id: ID вопроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        QuestionResponse: Данные вопроса

    Raises:
        HTTPException: Если вопрос не найден
    """
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    return question


@router.put("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: uuid.UUID,
    question_update: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить вопрос (ответить, изменить статус, закрепить).

    Args:
        question_id: ID вопроса
        question_update: Данные для обновления
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        QuestionResponse: Обновленный вопрос

    Raises:
        HTTPException: Если вопрос не найден или доступ запрещен
    """
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Проверяем права доступа - только владелец стрима может отвечать
    from src.models.stream import Stream
    stream = db.query(Stream).filter(Stream.id == question.stream_id).first()
    if stream.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only stream owner can answer questions"
        )

    # Обновляем поля
    if question_update.answer is not None:
        question.answer = question_update.answer
        if question_update.status is None:
            # Автоматически меняем статус на answered если не указан иной
            question.status = QuestionStatus.ANSWERED
            question.answered_at = datetime.now(timezone.utc)

    if question_update.status is not None:
        question.status = question_update.status
        if question_update.status == QuestionStatus.ANSWERED and question.answer:
            question.answered_at = datetime.now(timezone.utc)

    if question_update.is_pinned is not None:
        question.is_pinned = question_update.is_pinned

    db.commit()
    db.refresh(question)

    return question


@router.post("/questions/{question_id}/upvote", status_code=status.HTTP_200_OK)
def upvote_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Проголосовать за вопрос (upvote).

    Args:
        question_id: ID вопроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        dict: Результат голосования

    Raises:
        HTTPException: Если вопрос не найден или уже проголосован
    """
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Проверяем, есть ли уже upvote от этого пользователя
    existing_upvote = db.query(QuestionUpvote).filter(
        QuestionUpvote.question_id == question_id,
        QuestionUpvote.user_id == current_user.id
    ).first()

    if existing_upvote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already upvoted this question"
        )

    # Создаем upvote
    new_upvote = QuestionUpvote(
        question_id=question_id,
        user_id=current_user.id,
        telegram_user_id=current_user.telegram_id
    )

    db.add(new_upvote)

    # Обновляем кэшированный счетчик
    question.upvote_count += 1

    db.commit()

    return {
        "status": "success",
        "message": "Question upvoted",
        "upvote_count": question.upvote_count
    }


@router.delete("/questions/{question_id}/upvote", status_code=status.HTTP_200_OK)
def remove_upvote(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить свой upvote с вопроса.

    Args:
        question_id: ID вопроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        dict: Результат операции

    Raises:
        HTTPException: Если вопрос не найден или upvote не найден
    """
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Находим upvote от этого пользователя
    upvote = db.query(QuestionUpvote).filter(
        QuestionUpvote.question_id == question_id,
        QuestionUpvote.user_id == current_user.id
    ).first()

    if not upvote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have not upvoted this question"
        )

    # Удаляем upvote
    db.delete(upvote)

    # Обновляем кэшированный счетчик
    if question.upvote_count > 0:
        question.upvote_count -= 1

    db.commit()

    return {
        "status": "success",
        "message": "Upvote removed",
        "upvote_count": question.upvote_count
    }


@router.delete("/questions/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить вопрос (только для автора или владельца стрима).

    Args:
        question_id: ID вопроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        dict: Результат удаления

    Raises:
        HTTPException: Если вопрос не найден или доступ запрещен
    """
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Проверяем права доступа - автор вопроса или владелец стрима
    from src.models.stream import Stream
    stream = db.query(Stream).filter(Stream.id == question.stream_id).first()

    can_delete = (
        question.author_id == current_user.id or
        stream.owner_id == current_user.id
    )

    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only question author or stream owner can delete"
        )

    # Удаляем вопрос (каскадно удалятся upvotes)
    db.delete(question)
    db.commit()

    return {"status": "success", "message": "Question deleted"}
