from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.stream import Stream
from src.models.engagement import CTA, CTAStatus, ActionType
from api.auth import get_current_user
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import uuid

router = APIRouter()

class CTACreate(BaseModel):
    stream_id: uuid.UUID
    action_type: ActionType
    title: str
    message: Optional[str] = None
    action_url: Optional[str] = None
    button_text: Optional[str] = "Learn More"
    button_color: Optional[str] = None
    is_dismissable: Optional[bool] = True
    display_duration: Optional[int] = None
    position: Optional[str] = "bottom-right"
    priority: Optional[int] = 0
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class CTAResponse(BaseModel):
    id: uuid.UUID
    stream_id: uuid.UUID
    action_type: ActionType
    status: CTAStatus
    title: str
    message: Optional[str] = None
    action_url: Optional[str] = None
    button_text: str
    button_color: Optional[str] = None
    is_dismissable: bool
    display_duration: Optional[int] = None
    position: str
    priority: int
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    display_count: int
    dismiss_count: int
    click_count: int
    conversion_rate: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[CTAResponse])
def list_ctas(
    stream_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List CTAs for the current user's streams.
    Optionally filter by stream_id.
    """
    # Build query - only return CTAs for streams owned by current user
    query = db.query(CTA).join(Stream).filter(Stream.owner_id == current_user.id)

    # Filter by stream if provided
    if stream_id:
        # Verify stream belongs to user
        stream = db.query(Stream).filter(
            Stream.id == stream_id,
            Stream.owner_id == current_user.id
        ).first()
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found or access denied")
        query = query.filter(CTA.stream_id == stream_id)

    ctas = query.order_by(CTA.priority.desc(), CTA.created_at.desc()).all()
    return ctas

@router.post("/", response_model=CTAResponse)
def create_cta(
    cta_in: CTACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new CTA for a stream owned by the current user."""
    # Verify stream belongs to user
    stream = db.query(Stream).filter(
        Stream.id == cta_in.stream_id,
        Stream.owner_id == current_user.id
    ).first()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found or access denied")

    # Determine initial status based on scheduling
    initial_status = CTAStatus.DRAFT
    if cta_in.scheduled_at:
        if cta_in.scheduled_at <= datetime.now(timezone.utc):
            initial_status = CTAStatus.ACTIVE
        else:
            initial_status = CTAStatus.SCHEDULED
    else:
        initial_status = CTAStatus.ACTIVE

    new_cta = CTA(
        stream_id=cta_in.stream_id,
        created_by_id=current_user.id,
        action_type=cta_in.action_type,
        title=cta_in.title,
        message=cta_in.message,
        action_url=cta_in.action_url,
        button_text=cta_in.button_text,
        button_color=cta_in.button_color,
        is_dismissable=cta_in.is_dismissable,
        display_duration=cta_in.display_duration,
        position=cta_in.position,
        priority=cta_in.priority,
        scheduled_at=cta_in.scheduled_at,
        expires_at=cta_in.expires_at,
        status=initial_status,
        display_count=0,
        dismiss_count=0,
        click_count=0
    )

    db.add(new_cta)
    db.commit()
    db.refresh(new_cta)

    return new_cta

@router.post("/{cta_id}/display", response_model=CTAResponse)
def display_cta(
    cta_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a CTA as displayed (increment display_count).
    This is called when the CTA is shown on the overlay.
    """
    # Verify CTA exists and belongs to user's stream
    cta = db.query(CTA).join(Stream).filter(
        CTA.id == cta_id,
        Stream.owner_id == current_user.id
    ).first()

    if not cta:
        raise HTTPException(status_code=404, detail="CTA not found or access denied")

    # Increment display count
    cta.display_count += 1

    # Update status if needed
    if cta.status == CTAStatus.SCHEDULED:
        cta.status = CTAStatus.ACTIVE

    # Update conversion rate
    if cta.display_count > 0:
        cta.conversion_rate = int((cta.click_count / cta.display_count) * 100)

    db.commit()
    db.refresh(cta)

    return cta

@router.post("/{cta_id}/dismiss", response_model=CTAResponse)
def dismiss_cta(
    cta_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a CTA as dismissed (increment dismiss_count).
    This is called when a viewer closes the CTA.
    """
    # Verify CTA exists and belongs to user's stream
    cta = db.query(CTA).join(Stream).filter(
        CTA.id == cta_id,
        Stream.owner_id == current_user.id
    ).first()

    if not cta:
        raise HTTPException(status_code=404, detail="CTA not found or access denied")

    # Check if dismissable
    if not cta.is_dismissable:
        raise HTTPException(status_code=400, detail="CTA is not dismissable")

    # Increment dismiss count
    cta.dismiss_count += 1

    db.commit()
    db.refresh(cta)

    return cta

@router.post("/{cta_id}/click", response_model=CTAResponse)
def click_cta(
    cta_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a click on a CTA (increment click_count).
    This is called when a viewer clicks the CTA button.
    """
    # Verify CTA exists and belongs to user's stream
    cta = db.query(CTA).join(Stream).filter(
        CTA.id == cta_id,
        Stream.owner_id == current_user.id
    ).first()

    if not cta:
        raise HTTPException(status_code=404, detail="CTA not found or access denied")

    # Increment click count
    cta.click_count += 1

    # Update conversion rate
    if cta.display_count > 0:
        cta.conversion_rate = int((cta.click_count / cta.display_count) * 100)

    db.commit()
    db.refresh(cta)

    return cta

@router.get("/{cta_id}", response_model=CTAResponse)
def get_cta(
    cta_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific CTA by ID."""
    # Verify CTA exists and belongs to user's stream
    cta = db.query(CTA).join(Stream).filter(
        CTA.id == cta_id,
        Stream.owner_id == current_user.id
    ).first()

    if not cta:
        raise HTTPException(status_code=404, detail="CTA not found or access denied")

    return cta

@router.put("/{cta_id}", response_model=CTAResponse)
def update_cta(
    cta_id: uuid.UUID,
    cta_in: CTACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing CTA."""
    # Verify CTA exists and belongs to user's stream
    cta = db.query(CTA).join(Stream).filter(
        CTA.id == cta_id,
        Stream.owner_id == current_user.id
    ).first()

    if not cta:
        raise HTTPException(status_code=404, detail="CTA not found or access denied")

    # Update fields
    cta.action_type = cta_in.action_type
    cta.title = cta_in.title
    cta.message = cta_in.message
    cta.action_url = cta_in.action_url
    cta.button_text = cta_in.button_text
    cta.button_color = cta_in.button_color
    cta.is_dismissable = cta_in.is_dismissable
    cta.display_duration = cta_in.display_duration
    cta.position = cta_in.position
    cta.priority = cta_in.priority
    cta.scheduled_at = cta_in.scheduled_at
    cta.expires_at = cta_in.expires_at

    db.commit()
    db.refresh(cta)

    return cta

@router.delete("/{cta_id}")
def delete_cta(
    cta_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a CTA."""
    # Verify CTA exists and belongs to user's stream
    cta = db.query(CTA).join(Stream).filter(
        CTA.id == cta_id,
        Stream.owner_id == current_user.id
    ).first()

    if not cta:
        raise HTTPException(status_code=404, detail="CTA not found or access denied")

    db.delete(cta)
    db.commit()

    return {"status": "success", "message": "CTA deleted"}
