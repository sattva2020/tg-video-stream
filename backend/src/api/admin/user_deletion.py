"""
User Deletion Endpoints for GDPR Compliance
Spec: 025-advanced-security-compliance-features

Provides user account deletion functionality for GDPR right to erasure.
Admin-only access for permanently deleting user accounts and associated data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from api.auth import require_admin
from src.models.user import User
from database import get_db
from src.services.activity_service import ActivityService
from src.lib.audit import audit_delete
from pydantic import BaseModel

router = APIRouter()


class UserDeletionResponse(BaseModel):
    """Schema for user deletion response."""
    status: str
    message: str
    deleted_user_id: str
    deleted_user_email: Optional[str]


@router.delete("/users/{user_id}", response_model=UserDeletionResponse)
@audit_delete("user", "user_id")
async def delete_user_account(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a user account for GDPR right to erasure.

    Permanently deletes a user account and all associated data.
    This operation is irreversible and should be used with caution.
    Superadmin accounts cannot be deleted.

    Parameters:
        user_id: UUID of the user to delete

    Returns:
        UserDeletionResponse with deletion status

    Raises:
        404: If user not found
        403: If trying to delete superadmin or self

    Example:
        DELETE /api/admin/users/123e4567-e89b-12d3-a456-426614174000

        Response:
        {
            "status": "success",
            "message": "User account permanently deleted",
            "deleted_user_id": "123e4567-e89b-12d3-a456-426614174000",
            "deleted_user_email": "user@example.com"
        }
    """
    try:
        # Fetch the user to delete
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Protect superadmin accounts from deletion
        if getattr(user, 'role', '').lower() == 'superadmin':
            raise HTTPException(
                status_code=403,
                detail="Cannot delete superadmin account"
            )

        # Prevent self-deletion
        if user.id == current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete your own account"
            )

        # Store user info for logging before deletion
        deleted_user_id = str(user.id)
        deleted_user_email = user.email
        deleted_user_role = getattr(user, 'role', 'user')
        deleted_user_full_name = getattr(user, 'full_name', None)

        # Perform the deletion (cascade will handle related records)
        db.delete(user)
        db.commit()

        # Log the deletion activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="user_deleted",
            message=f"User account deleted: {deleted_user_email}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "deleted_user_id": deleted_user_id,
                "deleted_user_email": deleted_user_email,
                "deleted_user_role": deleted_user_role,
                "deleted_user_full_name": deleted_user_full_name,
                "deleted_by": current_user.email,
                "deletion_reason": "gdpr_right_to_erasure"
            }
        )

        return UserDeletionResponse(
            status="success",
            message="User account permanently deleted",
            deleted_user_id=deleted_user_id,
            deleted_user_email=deleted_user_email
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Roll back the session on error
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete user account: {str(e)}"
        )
