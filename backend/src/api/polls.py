"""
Poll API endpoints for interactive viewer polls.

Created for Feature 020 (Viewer Interaction & Engagement Features).
Provides REST API for creating, managing, and voting in polls.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
import uuid

from src.database import get_db
from src.models.user import User
from src.models.poll import Poll, PollOption, PollVote, PollType, PollStatus
from api.auth import get_current_user
from src.api.websocket import notify_poll_created, notify_poll_updated, notify_vote_cast

router = APIRouter()


# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================

class PollOptionCreate(BaseModel):
    """Модель для создания варианта ответа."""
    text: str
    order: int = 0


class PollOptionResponse(BaseModel):
    """Модель ответа для варианта опроса."""
    id: uuid.UUID
    text: str
    order: int
    vote_count: int

    model_config = ConfigDict(from_attributes=True)


class PollCreate(BaseModel):
    """Модель для создания опроса."""
    question: str
    description: Optional[str] = None
    poll_type: PollType = PollType.SINGLE_CHOICE
    allow_multiple_votes: bool = False
    is_anonymous: bool = True
    max_votes_per_user: Optional[int] = None
    options: List[PollOptionCreate]
    ended_at: Optional[datetime] = None


class PollResponse(BaseModel):
    """Модель ответа для опроса."""
    id: uuid.UUID
    question: str
    description: Optional[str] = None
    poll_type: PollType
    status: PollStatus
    allow_multiple_votes: bool
    is_anonymous: bool
    max_votes_per_user: Optional[int] = None
    owner_id: uuid.UUID
    options: List[PollOptionResponse]
    total_votes: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VoteCreate(BaseModel):
    """Модель для голосования."""
    option_ids: List[uuid.UUID]  # Список для поддержки multiple choice


# =============================================================================
# Poll Endpoints
# =============================================================================

@router.get("/", response_model=List[PollResponse])
def list_polls(
    status_filter: Optional[PollStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список опросов.

    Args:
        status_filter: Фильтр по статусу (опционально)
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        List[PollResponse]: Список опросов
    """
    query = db.query(Poll).filter(Poll.owner_id == current_user.id)

    if status_filter:
        query = query.filter(Poll.status == status_filter)

    polls = query.order_by(Poll.created_at.desc()).all()

    # Обогащаем данными о количестве голосов
    result = []
    for poll in polls:
        total_votes = db.query(PollVote).filter(PollVote.poll_id == poll.id).count()
        poll_dict = PollResponse.model_validate(poll).model_dump()
        poll_dict["total_votes"] = total_votes
        result.append(PollResponse(**poll_dict))

    return result


@router.post("/", response_model=PollResponse)
def create_poll(
    poll_in: PollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать новый опрос.

    Args:
        poll_in: Данные для создания опроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        PollResponse: Созданный опрос

    Raises:
        HTTPException: Если варианты ответа не предоставлены или недействительны
    """
    if not poll_in.options or len(poll_in.options) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll must have at least 2 options"
        )

    # Проверка на соответствие типа опроса и количества вариантов
    if poll_in.poll_type == PollType.SINGLE_CHOICE and len(poll_in.options) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Single choice poll must have at least 2 options"
        )

    # Создаем опрос
    new_poll = Poll(
        question=poll_in.question,
        description=poll_in.description,
        poll_type=poll_in.poll_type,
        status=PollStatus.DRAFT,
        allow_multiple_votes=poll_in.allow_multiple_votes,
        is_anonymous=poll_in.is_anonymous,
        max_votes_per_user=poll_in.max_votes_per_user,
        owner_id=current_user.id,
        ended_at=poll_in.ended_at
    )

    db.add(new_poll)
    db.flush()  # Чтобы получить ID для создания вариантов

    # Создаем варианты ответа
    for option_in in poll_in.options:
        option = PollOption(
            poll_id=new_poll.id,
            text=option_in.text,
            order=option_in.order
        )
        db.add(option)

    db.commit()
    db.refresh(new_poll)

    # Уведомляем через WebSocket (асинхронно)
    import asyncio
    asyncio.create_task(notify_poll_created(new_poll))

    return new_poll


@router.get("/{poll_id}", response_model=PollResponse)
def get_poll(
    poll_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить опрос по ID.

    Args:
        poll_id: ID опроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        PollResponse: Данные опроса

    Raises:
        HTTPException: Если опрос не найден
    """
    poll = db.query(Poll).filter(Poll.id == poll_id).first()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    # Проверяем права доступа (только владелец может просматривать свои черновики)
    if poll.owner_id != current_user.id and poll.status == PollStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to draft polls"
        )

    # Подсчитываем общее количество голосов
    total_votes = db.query(PollVote).filter(PollVote.poll_id == poll.id).count()

    poll_dict = PollResponse.model_validate(poll).model_dump()
    poll_dict["total_votes"] = total_votes

    return PollResponse(**poll_dict)


@router.post("/{poll_id}/vote", status_code=status.HTTP_200_OK)
def vote_poll(
    poll_id: uuid.UUID,
    vote_in: VoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Проголосовать в опросе.

    Args:
        poll_id: ID опроса
        vote_in: Данные голоса (список option_ids)
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        dict: Результат голосования

    Raises:
        HTTPException: Если опрос не найден, закрыт, или голосование недействительно
    """
    poll = db.query(Poll).filter(Poll.id == poll_id).first()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    if poll.status != PollStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot vote on poll with status {poll.status}"
        )

    # Проверка срока действия
    if poll.ended_at and poll.ended_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll has ended"
        )

    # Проверяем варианты ответа
    if not vote_in.option_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one option must be selected"
        )

    # Проверяем, что варианты принадлежат этому опросу
    valid_options = db.query(PollOption).filter(
        PollOption.poll_id == poll_id,
        PollOption.id.in_(vote_in.option_ids)
    ).all()

    if len(valid_options) != len(vote_in.option_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more options are invalid"
        )

    # Проверка типа опроса
    if poll.poll_type == PollType.SINGLE_CHOICE and len(vote_in.option_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Single choice poll allows only one option"
        )

    # Проверка на повторное голосование
    if not poll.allow_multiple_votes:
        existing_vote = db.query(PollVote).filter(
            PollVote.poll_id == poll_id,
            PollVote.user_id == current_user.id
        ).first()

        if existing_vote:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already voted in this poll"
            )

    # Проверка максимального количества голосов
    if poll.max_votes_per_user:
        vote_count = db.query(PollVote).filter(
            PollVote.poll_id == poll_id,
            PollVote.user_id == current_user.id
        ).count()

        if vote_count >= poll.max_votes_per_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum votes per user ({poll.max_votes_per_user}) exceeded"
            )

    # Создаем голоса
    for option_id in vote_in.option_ids:
        vote = PollVote(
            poll_id=poll_id,
            option_id=option_id,
            user_id=None if poll.is_anonymous else current_user.id
        )
        db.add(vote)

        # Обновляем счетчик голосов для варианта
        option = next((o for o in valid_options if o.id == option_id), None)
        if option:
            option.vote_count += 1

    db.commit()

    # Уведомляем через WebSocket (асинхронно)
    import asyncio
    asyncio.create_task(notify_vote_cast(str(poll_id), [str(oid) for oid in vote_in.option_ids]))

    return {"status": "success", "message": "Vote cast successfully"}


@router.post("/{poll_id}/start", response_model=PollResponse)
def start_poll(
    poll_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Запустить опрос (изменить статус с DRAFT на ACTIVE).

    Args:
        poll_id: ID опроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        PollResponse: Обновленный опрос

    Raises:
        HTTPException: Если опрос не найден или доступ запрещен
    """
    poll = db.query(Poll).filter(Poll.id == poll_id).first()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    if poll.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if poll.status != PollStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start poll with status {poll.status}"
        )

    poll.status = PollStatus.ACTIVE
    poll.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(poll)

    # Уведомляем через WebSocket (асинхронно)
    import asyncio
    asyncio.create_task(notify_poll_updated(poll))

    return poll


@router.post("/{poll_id}/close", response_model=PollResponse)
def close_poll(
    poll_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Закрыть опрос.

    Args:
        poll_id: ID опроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        PollResponse: Обновленный опрос

    Raises:
        HTTPException: Если опрос не найден или доступ запрещен
    """
    poll = db.query(Poll).filter(Poll.id == poll_id).first()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    if poll.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if poll.status == PollStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll is already closed"
        )

    poll.status = PollStatus.CLOSED
    poll.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(poll)

    # Уведомляем через WebSocket (асинхронно)
    import asyncio
    asyncio.create_task(notify_poll_updated(poll))

    return poll


@router.delete("/{poll_id}", status_code=status.HTTP_200_OK)
def delete_poll(
    poll_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить опрос.

    Args:
        poll_id: ID опроса
        db: Сессия БД
        current_user: Текущий авторизованный пользователь

    Returns:
        dict: Результат удаления

    Raises:
        HTTPException: Если опрос не найден или доступ запрещен
    """
    poll = db.query(Poll).filter(Poll.id == poll_id).first()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    if poll.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Удаляем опрос (каскадно удалятся варианты и голоса)
    db.delete(poll)
    db.commit()

    return {"status": "success", "message": "Poll deleted"}
