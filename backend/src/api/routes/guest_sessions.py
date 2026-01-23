"""
API routes for guest co-hosting session management.

Endpoints:
  POST /api/v1/live/guests/invite - Invite a guest to co-host
  GET /api/v1/live/guests - List all guests for a stream
  GET /api/v1/live/guests/{guest_id} - Get guest session details
  PUT /api/v1/live/guests/{guest_id} - Update guest permissions
  DELETE /api/v1/live/guests/{guest_id} - Remove guest from stream
  POST /api/v1/live/guests/{guest_id}/accept - Accept guest invitation
  POST /api/v1/live/guests/{guest_id}/reject - Reject guest invitation
  POST /api/v1/live/guests/{guest_id}/join - Guest joins the session
  POST /api/v1/live/guests/{guest_id}/leave - Guest leaves the session
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
import logging
import uuid
import secrets
from datetime import datetime
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, require_admin
from ...models.guest_session import GuestSession, GuestSessionStatus, GuestPermission
from ...models.live_stream import LiveStream
from ...models.user import User
from ...database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/live/guests", tags=["guest-sessions"])


# Request/Response Models
class InviteGuestRequest(BaseModel):
    """Request to invite a guest to co-host."""
    stream_id: uuid.UUID = Field(description="Live stream ID")
    guest_email: EmailStr = Field(description="Guest email address")
    invite_message: Optional[str] = Field(None, max_length=500, description="Personal message for the guest")
    can_speak: Optional[bool] = Field(True, description="Permission to use microphone")
    can_share_video: Optional[bool] = Field(True, description="Permission to use camera")
    can_share_screen: Optional[bool] = Field(False, description="Permission to share screen")
    can_control_stream: Optional[bool] = Field(False, description="Permission to control stream")
    can_invite_others: Optional[bool] = Field(False, description="Permission to invite other guests")


class UpdateGuestPermissionsRequest(BaseModel):
    """Request to update guest permissions."""
    can_speak: Optional[bool] = Field(None, description="Permission to use microphone")
    can_share_video: Optional[bool] = Field(None, description="Permission to use camera")
    can_share_screen: Optional[bool] = Field(None, description="Permission to share screen")
    can_control_stream: Optional[bool] = Field(None, description="Permission to control stream")
    can_invite_others: Optional[bool] = Field(None, description="Permission to invite other guests")


class RejectInvitationRequest(BaseModel):
    """Request to reject guest invitation."""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")


class LeaveSessionRequest(BaseModel):
    """Request to leave guest session."""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for leaving")


class GuestSessionResponse(BaseModel):
    """Response with guest session information."""
    id: uuid.UUID
    live_stream_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    can_speak: bool
    can_share_video: bool
    can_share_screen: bool
    can_control_stream: bool
    can_invite_others: bool
    webrtc_connection_id: Optional[str]
    connection_quality: Optional[str]
    invite_token: Optional[str]
    invite_message: Optional[str]
    rejection_reason: Optional[str]
    leave_reason: Optional[str]
    created_at: str
    joined_at: Optional[str]
    left_at: Optional[str]
    last_active_at: Optional[str]


class GuestSessionListResponse(BaseModel):
    """Response with list of guest sessions."""
    total: int
    guests: List[GuestSessionResponse]
    stream_id: uuid.UUID


class InviteGuestResponse(BaseModel):
    """Response after inviting a guest."""
    guest_id: uuid.UUID
    invite_token: str
    invite_url: str
    message: str


# Route Handlers

@router.post("/invite", response_model=InviteGuestResponse, status_code=201)
async def invite_guest(
    request: InviteGuestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invite a guest to co-host a live stream.

    **Permission**: Stream owner only

    **Rate Limit**: 10 requests/minute per user (Strict)

    **Example**:
    ```json
    {
      "stream_id": "123e4567-e89b-12d3-a456-426614174000",
      "guest_email": "guest@example.com",
      "invite_message": "Join my stream for an interview!",
      "can_speak": true,
      "can_share_video": true,
      "can_share_screen": false,
      "can_control_stream": false,
      "can_invite_others": false
    }
    ```
    """
    try:
        # Get stream and verify ownership
        stream = db.query(LiveStream).filter(LiveStream.id == request.stream_id).first()
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        if stream.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only invite guests to your own streams"
            )

        # Find guest user by email
        guest_user = db.query(User).filter(User.email == request.guest_email).first()
        if not guest_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest user not found"
            )

        # Check if guest is already invited
        existing_session = db.query(GuestSession).filter(
            GuestSession.live_stream_id == request.stream_id,
            GuestSession.user_id == guest_user.id
        ).first()

        if existing_session:
            # If existing session is in a terminal state, allow re-invite
            if existing_session.status in [GuestSessionStatus.LEFT, GuestSessionStatus.REJECTED, GuestSessionStatus.KICKED]:
                db.delete(existing_session)
                db.commit()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Guest already has a {existing_session.status} session"
                )

        # Check guest limit
        active_guest_count = db.query(GuestSession).filter(
            GuestSession.live_stream_id == request.stream_id,
            GuestSession.status.in_([GuestSessionStatus.PENDING, GuestSessionStatus.ACCEPTED, GuestSessionStatus.ACTIVE])
        ).count()

        if active_guest_count >= stream.max_guests:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum guest limit ({stream.max_guests}) reached for this stream"
            )

        # Generate invite token
        invite_token = secrets.token_urlsafe(32)

        # Create guest session
        guest_session = GuestSession(
            live_stream_id=request.stream_id,
            user_id=guest_user.id,
            status=GuestSessionStatus.PENDING,
            can_speak=request.can_speak,
            can_share_video=request.can_share_video,
            can_share_screen=request.can_share_screen,
            can_control_stream=request.can_control_stream,
            can_invite_others=request.can_invite_others,
            invite_token=invite_token,
            invite_message=request.invite_message
        )

        db.add(guest_session)
        db.commit()
        db.refresh(guest_session)

        # Generate invite URL
        invite_url = f"/live/guest/join?token={invite_token}"

        logger.info(f"User {current_user.id} invited guest {guest_user.id} to stream {request.stream_id}")

        return InviteGuestResponse(
            guest_id=guest_session.id,
            invite_token=invite_token,
            invite_url=invite_url,
            message=f"Invitation sent to {request.guest_email}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting guest: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invite guest"
        )


@router.get("", response_model=GuestSessionListResponse, status_code=200)
async def list_guests(
    stream_id: uuid.UUID = Query(..., description="Live stream ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all guests for a live stream.

    **Permission**: Authenticated user only

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Query Parameters**:
    - `stream_id`: Live stream ID (required)
    - `status_filter`: Filter by status (pending, accepted, active, rejected, left, kicked)
    """
    try:
        # Verify stream exists
        stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live stream not found"
            )

        # Build query
        query = db.query(GuestSession).filter(GuestSession.live_stream_id == stream_id)

        if status_filter:
            try:
                status_enum = GuestSessionStatus(status_filter)
                query = query.filter(GuestSession.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}"
                )

        guest_sessions = query.all()

        guests = [GuestSessionResponse(
            id=str(g.id),
            live_stream_id=str(g.live_stream_id),
            user_id=str(g.user_id),
            status=g.status.value,
            can_speak=g.can_speak,
            can_share_video=g.can_share_video,
            can_share_screen=g.can_share_screen,
            can_control_stream=g.can_control_stream,
            can_invite_others=g.can_invite_others,
            webrtc_connection_id=g.webrtc_connection_id,
            connection_quality=g.connection_quality,
            invite_token=g.invite_token,
            invite_message=g.invite_message,
            rejection_reason=g.rejection_reason,
            leave_reason=g.leave_reason,
            created_at=g.created_at.isoformat() if g.created_at else None,
            joined_at=g.joined_at.isoformat() if g.joined_at else None,
            left_at=g.left_at.isoformat() if g.left_at else None,
            last_active_at=g.last_active_at.isoformat() if g.last_active_at else None
        ) for g in guest_sessions]

        return GuestSessionListResponse(
            total=len(guests),
            guests=guests,
            stream_id=stream_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing guests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list guests"
        )


@router.get("/{guest_id}", response_model=GuestSessionResponse, status_code=200)
async def get_guest_session(
    guest_id: uuid.UUID = Path(..., description="Guest session ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific guest session.

    **Permission**: Guest or stream owner only

    **Rate Limit**: 200 requests/minute per user (Elevated)
    """
    try:
        guest_session = db.query(GuestSession).filter(GuestSession.id == guest_id).first()

        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest session not found"
            )

        # Verify access permissions (guest or stream owner)
        stream = db.query(LiveStream).filter(LiveStream.id == guest_session.live_stream_id).first()
        if not stream or (stream.owner_id != current_user.id and guest_session.user_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this guest session"
            )

        return GuestSessionResponse(
            id=str(guest_session.id),
            live_stream_id=str(guest_session.live_stream_id),
            user_id=str(guest_session.user_id),
            status=guest_session.status.value,
            can_speak=guest_session.can_speak,
            can_share_video=guest_session.can_share_video,
            can_share_screen=guest_session.can_share_screen,
            can_control_stream=guest_session.can_control_stream,
            can_invite_others=guest_session.can_invite_others,
            webrtc_connection_id=guest_session.webrtc_connection_id,
            connection_quality=guest_session.connection_quality,
            invite_token=guest_session.invite_token,
            invite_message=guest_session.invite_message,
            rejection_reason=guest_session.rejection_reason,
            leave_reason=guest_session.leave_reason,
            created_at=guest_session.created_at.isoformat() if guest_session.created_at else None,
            joined_at=guest_session.joined_at.isoformat() if guest_session.joined_at else None,
            left_at=guest_session.left_at.isoformat() if guest_session.left_at else None,
            last_active_at=guest_session.last_active_at.isoformat() if guest_session.last_active_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting guest session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get guest session"
        )


@router.put("/{guest_id}", response_model=GuestSessionResponse, status_code=200)
async def update_guest_permissions(
    guest_id: uuid.UUID = Path(..., description="Guest session ID"),
    request: UpdateGuestPermissionsRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update guest permissions.

    **Permission**: Stream owner only

    **Rate Limit**: 50 requests/minute per user (Standard)

    **Example**:
    ```json
    {
      "can_speak": true,
      "can_share_video": false,
      "can_share_screen": false,
      "can_control_stream": false,
      "can_invite_others": false
    }
    ```
    """
    try:
        # Get guest session
        guest_session = db.query(GuestSession).filter(GuestSession.id == guest_id).first()

        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest session not found"
            )

        # Verify stream ownership
        stream = db.query(LiveStream).filter(LiveStream.id == guest_session.live_stream_id).first()
        if not stream or stream.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update guests for your own streams"
            )

        # Update permissions
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(guest_session, field, value)

        db.commit()
        db.refresh(guest_session)

        logger.info(f"User {current_user.id} updated permissions for guest {guest_id}")

        return GuestSessionResponse(
            id=str(guest_session.id),
            live_stream_id=str(guest_session.live_stream_id),
            user_id=str(guest_session.user_id),
            status=guest_session.status.value,
            can_speak=guest_session.can_speak,
            can_share_video=guest_session.can_share_video,
            can_share_screen=guest_session.can_share_screen,
            can_control_stream=guest_session.can_control_stream,
            can_invite_others=guest_session.can_invite_others,
            webrtc_connection_id=guest_session.webrtc_connection_id,
            connection_quality=guest_session.connection_quality,
            invite_token=guest_session.invite_token,
            invite_message=guest_session.invite_message,
            rejection_reason=guest_session.rejection_reason,
            leave_reason=guest_session.leave_reason,
            created_at=guest_session.created_at.isoformat() if guest_session.created_at else None,
            joined_at=guest_session.joined_at.isoformat() if guest_session.joined_at else None,
            left_at=guest_session.left_at.isoformat() if guest_session.left_at else None,
            last_active_at=guest_session.last_active_at.isoformat() if guest_session.last_active_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating guest permissions: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update guest permissions"
        )


@router.delete("/{guest_id}", status_code=204)
async def remove_guest(
    guest_id: uuid.UUID = Path(..., description="Guest session ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a guest from the stream.

    **Permission**: Stream owner only

    **Rate Limit**: 10 requests/minute per user (Strict)
    """
    try:
        # Get guest session
        guest_session = db.query(GuestSession).filter(GuestSession.id == guest_id).first()

        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest session not found"
            )

        # Verify stream ownership
        stream = db.query(LiveStream).filter(LiveStream.id == guest_session.live_stream_id).first()
        if not stream or stream.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only remove guests from your own streams"
            )

        # Mark as kicked
        guest_session.status = GuestSessionStatus.KICKED
        guest_session.left_at = datetime.utcnow()
        db.commit()

        logger.info(f"User {current_user.id} removed guest {guest_id} from stream")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing guest: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove guest"
        )


@router.post("/{guest_id}/accept", response_model=GuestSessionResponse, status_code=200)
async def accept_invitation(
    guest_id: uuid.UUID = Path(..., description="Guest session ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept a guest invitation.

    **Permission**: Invited guest only

    **Rate Limit**: 20 requests/minute per user (Standard)
    """
    try:
        # Get guest session
        guest_session = db.query(GuestSession).filter(GuestSession.id == guest_id).first()

        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest session not found"
            )

        # Verify the current user is the invited guest
        if guest_session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only accept your own invitations"
            )

        # Check status
        if guest_session.status != GuestSessionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept invitation with status: {guest_session.status.value}"
            )

        # Update status
        guest_session.status = GuestSessionStatus.ACCEPTED
        guest_session.last_active_at = datetime.utcnow()
        db.commit()
        db.refresh(guest_session)

        logger.info(f"User {current_user.id} accepted invitation to stream {guest_session.live_stream_id}")

        return GuestSessionResponse(
            id=str(guest_session.id),
            live_stream_id=str(guest_session.live_stream_id),
            user_id=str(guest_session.user_id),
            status=guest_session.status.value,
            can_speak=guest_session.can_speak,
            can_share_video=guest_session.can_share_video,
            can_share_screen=guest_session.can_share_screen,
            can_control_stream=guest_session.can_control_stream,
            can_invite_others=guest_session.can_invite_others,
            webrtc_connection_id=guest_session.webrtc_connection_id,
            connection_quality=guest_session.connection_quality,
            invite_token=guest_session.invite_token,
            invite_message=guest_session.invite_message,
            rejection_reason=guest_session.rejection_reason,
            leave_reason=guest_session.leave_reason,
            created_at=guest_session.created_at.isoformat() if guest_session.created_at else None,
            joined_at=guest_session.joined_at.isoformat() if guest_session.joined_at else None,
            left_at=guest_session.left_at.isoformat() if guest_session.left_at else None,
            last_active_at=guest_session.last_active_at.isoformat() if guest_session.last_active_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation"
        )


@router.post("/{guest_id}/reject", response_model=GuestSessionResponse, status_code=200)
async def reject_invitation(
    guest_id: uuid.UUID = Path(..., description="Guest session ID"),
    request: RejectInvitationRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a guest invitation.

    **Permission**: Invited guest only

    **Rate Limit**: 20 requests/minute per user (Standard)

    **Example**:
    ```json
    {
      "reason": "Cannot make it at this time"
    }
    ```
    """
    try:
        # Get guest session
        guest_session = db.query(GuestSession).filter(GuestSession.id == guest_id).first()

        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest session not found"
            )

        # Verify the current user is the invited guest
        if guest_session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reject your own invitations"
            )

        # Check status
        if guest_session.status != GuestSessionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject invitation with status: {guest_session.status.value}"
            )

        # Mark as rejected
        guest_session.mark_as_rejected(reason=request.reason if request else None)
        db.commit()
        db.refresh(guest_session)

        logger.info(f"User {current_user.id} rejected invitation to stream {guest_session.live_stream_id}")

        return GuestSessionResponse(
            id=str(guest_session.id),
            live_stream_id=str(guest_session.live_stream_id),
            user_id=str(guest_session.user_id),
            status=guest_session.status.value,
            can_speak=guest_session.can_speak,
            can_share_video=guest_session.can_share_video,
            can_share_screen=guest_session.can_share_screen,
            can_control_stream=guest_session.can_control_stream,
            can_invite_others=guest_session.can_invite_others,
            webrtc_connection_id=guest_session.webrtc_connection_id,
            connection_quality=guest_session.connection_quality,
            invite_token=guest_session.invite_token,
            invite_message=guest_session.invite_message,
            rejection_reason=guest_session.rejection_reason,
            leave_reason=guest_session.leave_reason,
            created_at=guest_session.created_at.isoformat() if guest_session.created_at else None,
            joined_at=guest_session.joined_at.isoformat() if guest_session.joined_at else None,
            left_at=guest_session.left_at.isoformat() if guest_session.left_at else None,
            last_active_at=guest_session.last_active_at.isoformat() if guest_session.last_active_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting invitation: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject invitation"
        )


@router.post("/{guest_id}/join", response_model=GuestSessionResponse, status_code=200)
async def join_session(
    guest_id: uuid.UUID = Path(..., description="Guest session ID"),
    webrtc_connection_id: Optional[str] = Query(None, description="WebRTC connection ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Guest joins the live session (after accepting).

    **Permission**: Accepted guest only

    **Rate Limit**: 20 requests/minute per user (Standard)

    **Notes**:
    - Establishes WebRTC connection
    - Marks guest as ACTIVE
    """
    try:
        # Get guest session
        guest_session = db.query(GuestSession).filter(GuestSession.id == guest_id).first()

        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest session not found"
            )

        # Verify the current user is the guest
        if guest_session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only join your own sessions"
            )

        # Check status
        if guest_session.status != GuestSessionStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot join session with status: {guest_session.status.value}"
            )

        # Mark as joined/active
        guest_session.mark_as_joined()
        if webrtc_connection_id:
            guest_session.webrtc_connection_id = webrtc_connection_id

        db.commit()
        db.refresh(guest_session)

        logger.info(f"User {current_user.id} joined stream session {guest_session.live_stream_id}")

        return GuestSessionResponse(
            id=str(guest_session.id),
            live_stream_id=str(guest_session.live_stream_id),
            user_id=str(guest_session.user_id),
            status=guest_session.status.value,
            can_speak=guest_session.can_speak,
            can_share_video=guest_session.can_share_video,
            can_share_screen=guest_session.can_share_screen,
            can_control_stream=guest_session.can_control_stream,
            can_invite_others=guest_session.can_invite_others,
            webrtc_connection_id=guest_session.webrtc_connection_id,
            connection_quality=guest_session.connection_quality,
            invite_token=guest_session.invite_token,
            invite_message=guest_session.invite_message,
            rejection_reason=guest_session.rejection_reason,
            leave_reason=guest_session.leave_reason,
            created_at=guest_session.created_at.isoformat() if guest_session.created_at else None,
            joined_at=guest_session.joined_at.isoformat() if guest_session.joined_at else None,
            left_at=guest_session.left_at.isoformat() if guest_session.left_at else None,
            last_active_at=guest_session.last_active_at.isoformat() if guest_session.last_active_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining session: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join session"
        )


@router.post("/{guest_id}/leave", response_model=GuestSessionResponse, status_code=200)
async def leave_session(
    guest_id: uuid.UUID = Path(..., description="Guest session ID"),
    request: LeaveSessionRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Guest leaves the live session.

    **Permission**: Active guest only

    **Rate Limit**: 20 requests/minute per user (Standard)

    **Example**:
    ```json
    {
      "reason": "Technical difficulties"
    }
    ```
    """
    try:
        # Get guest session
        guest_session = db.query(GuestSession).filter(GuestSession.id == guest_id).first()

        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guest session not found"
            )

        # Verify the current user is the guest
        if guest_session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only leave your own sessions"
            )

        # Check status
        if not guest_session.is_active():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot leave session with status: {guest_session.status.value}"
            )

        # Mark as left
        guest_session.mark_as_left(reason=request.reason if request else None)
        db.commit()
        db.refresh(guest_session)

        logger.info(f"User {current_user.id} left stream session {guest_session.live_stream_id}")

        return GuestSessionResponse(
            id=str(guest_session.id),
            live_stream_id=str(guest_session.live_stream_id),
            user_id=str(guest_session.user_id),
            status=guest_session.status.value,
            can_speak=guest_session.can_speak,
            can_share_video=guest_session.can_share_video,
            can_share_screen=guest_session.can_share_screen,
            can_control_stream=guest_session.can_control_stream,
            can_invite_others=guest_session.can_invite_others,
            webrtc_connection_id=guest_session.webrtc_connection_id,
            connection_quality=guest_session.connection_quality,
            invite_token=guest_session.invite_token,
            invite_message=guest_session.invite_message,
            rejection_reason=guest_session.rejection_reason,
            leave_reason=guest_session.leave_reason,
            created_at=guest_session.created_at.isoformat() if guest_session.created_at else None,
            joined_at=guest_session.joined_at.isoformat() if guest_session.joined_at else None,
            left_at=guest_session.left_at.isoformat() if guest_session.left_at else None,
            last_active_at=guest_session.last_active_at.isoformat() if guest_session.last_active_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error leaving session: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave session"
        )
