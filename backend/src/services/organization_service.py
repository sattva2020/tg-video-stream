from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import re
import uuid
from typing import Optional, List

from src.models.organization import Organization
from src.models.organization_user import OrganizationUser, OrganizationRole, OrganizationUserStatus
from src.models.user import User
from src.models.subscription import Subscription, PlanType, SubscriptionStatus


class OrganizationService:
    """Service for managing organization CRUD operations."""

    def create_organization(
        self,
        db: Session,
        name: str,
        slug: Optional[str] = None,
        logo_url: Optional[str] = None,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        custom_domain: Optional[str] = None,
        created_by_user_id: Optional[str] = None
    ) -> Organization:
        """
        Create a new organization with trial subscription.

        Args:
            db: Database session
            name: Organization name
            slug: Optional URL-friendly slug (auto-generated if not provided)
            logo_url: Optional logo URL
            primary_color: Optional primary hex color
            secondary_color: Optional secondary hex color
            custom_domain: Optional custom domain
            created_by_user_id: Optional user ID who is creating the organization

        Returns:
            Created Organization instance
        """
        # Generate slug if not provided
        if not slug:
            slug = self._generate_slug(name)

        # Check if slug is already taken
        existing = db.query(Organization).filter(Organization.slug == slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Organization with slug '{slug}' already exists"
            )

        # Validate hex colors if provided
        if primary_color and not self._is_valid_hex_color(primary_color):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid primary_color format. Use hex format #RRGGBB"
            )
        if secondary_color and not self._is_valid_hex_color(secondary_color):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid secondary_color format. Use hex format #RRGGBB"
            )

        # Create organization
        organization = Organization(
            name=name,
            slug=slug,
            logo_url=logo_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            custom_domain=custom_domain,
            is_active=True
        )
        db.add(organization)
        db.flush()  # Get organization ID without committing

        # Create trial subscription
        trial_subscription = Subscription(
            organization_id=organization.id,
            plan_type=PlanType.TRIAL.value,
            status=SubscriptionStatus.TRIALING.value
        )
        db.add(trial_subscription)

        # Create default roles (admin and member)
        admin_role = OrganizationRole(
            organization_id=organization.id,
            name="Admin",
            description="Organization administrator with full permissions",
            permissions={
                "manage_organization": True,
                "manage_members": True,
                "manage_streams": True,
                "manage_playlists": True,
                "manage_quotas": True,
                "manage_billing": True
            },
            is_system_role=True
        )
        db.add(admin_role)

        member_role = OrganizationRole(
            organization_id=organization.id,
            name="Member",
            description="Standard organization member",
            permissions={
                "manage_streams": True,
                "manage_playlists": True,
                "view_quotas": True
            },
            is_system_role=True
        )
        db.add(member_role)

        # Add creator as first member if provided
        if created_by_user_id:
            # Verify user exists
            user = db.query(User).filter(User.id == created_by_user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Create organization membership
            org_user = OrganizationUser(
                organization_id=organization.id,
                user_id=created_by_user_id,
                role_id=admin_role.id,
                status=OrganizationUserStatus.ACTIVE.value,
                joined_at=datetime.now(timezone.utc)
            )
            db.add(org_user)

            # Update user's organization
            user.organization_id = organization.id

        db.commit()
        db.refresh(organization)
        return organization

    def get_organization(self, db: Session, organization_id: str) -> Organization:
        """
        Get organization by ID.

        Args:
            db: Database session
            organization_id: Organization UUID

        Returns:
            Organization instance

        Raises:
            HTTPException: If organization not found
        """
        organization = db.query(Organization).filter(Organization.id == organization_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return organization

    def get_organization_by_slug(self, db: Session, slug: str) -> Organization:
        """
        Get organization by slug.

        Args:
            db: Database session
            slug: Organization slug

        Returns:
            Organization instance

        Raises:
            HTTPException: If organization not found
        """
        organization = db.query(Organization).filter(Organization.slug == slug).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return organization

    def update_organization(
        self,
        db: Session,
        organization_id: str,
        name: Optional[str] = None,
        logo_url: Optional[str] = None,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        custom_domain: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Organization:
        """
        Update organization details.

        Args:
            db: Database session
            organization_id: Organization UUID
            name: Optional new name
            logo_url: Optional new logo URL
            primary_color: Optional new primary hex color
            secondary_color: Optional new secondary hex color
            custom_domain: Optional new custom domain
            is_active: Optional active status

        Returns:
            Updated Organization instance
        """
        organization = self.get_organization(db, organization_id)

        # Validate hex colors if provided
        if primary_color and not self._is_valid_hex_color(primary_color):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid primary_color format. Use hex format #RRGGBB"
            )
        if secondary_color and not self._is_valid_hex_color(secondary_color):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid secondary_color format. Use hex format #RRGGBB"
            )

        # Check custom domain uniqueness if changed
        if custom_domain and custom_domain != organization.custom_domain:
            existing = db.query(Organization).filter(
                Organization.custom_domain == custom_domain,
                Organization.id != organization_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Custom domain '{custom_domain}' is already in use"
                )

        # Update fields
        if name is not None:
            organization.name = name
        if logo_url is not None:
            organization.logo_url = logo_url
        if primary_color is not None:
            organization.primary_color = primary_color
        if secondary_color is not None:
            organization.secondary_color = secondary_color
        if custom_domain is not None:
            organization.custom_domain = custom_domain
        if is_active is not None:
            organization.is_active = is_active

        db.commit()
        db.refresh(organization)
        return organization

    def deactivate_organization(self, db: Session, organization_id: str) -> Organization:
        """
        Deactivate an organization (soft delete).

        Args:
            db: Database session
            organization_id: Organization UUID

        Returns:
            Deactivated Organization instance
        """
        organization = self.get_organization(db, organization_id)
        organization.is_active = False
        db.commit()
        db.refresh(organization)
        return organization

    def delete_organization(self, db: Session, organization_id: str) -> None:
        """
        Permanently delete an organization.

        WARNING: This will cascade delete all related data.

        Args:
            db: Database session
            organization_id: Organization UUID
        """
        organization = self.get_organization(db, organization_id)
        db.delete(organization)
        db.commit()

    def list_organizations(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
        user_id: Optional[str] = None
    ) -> List[Organization]:
        """
        List organizations with optional filtering.

        Args:
            db: Database session
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive organizations
            user_id: Optional filter by user's organization

        Returns:
            List of Organization instances
        """
        query = db.query(Organization)

        if not include_inactive:
            query = query.filter(Organization.is_active == True)

        if user_id:
            query = query.filter(Organization.id == user_id)

        return query.offset(skip).limit(limit).all()

    def add_member(
        self,
        db: Session,
        organization_id: str,
        user_id: str,
        role_id: Optional[str] = None,
        invited_by: Optional[str] = None
    ) -> OrganizationUser:
        """
        Add a user to an organization.

        Args:
            db: Database session
            organization_id: Organization UUID
            user_id: User UUID to add
            role_id: Optional role UUID (defaults to member role)
            invited_by: Optional user UUID who sent the invitation

        Returns:
            Created OrganizationUser instance
        """
        # Verify organization exists
        organization = self.get_organization(db, organization_id)

        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if user is already a member
        existing = db.query(OrganizationUser).filter(
            OrganizationUser.organization_id == organization_id,
            OrganizationUser.user_id == user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization"
            )

        # Get default member role if none specified
        if not role_id:
            member_role = db.query(OrganizationRole).filter(
                OrganizationRole.organization_id == organization_id,
                OrganizationRole.name == "Member"
            ).first()
            if not member_role:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Default Member role not found"
                )
            role_id = member_role.id
        else:
            # Verify role exists and belongs to organization
            role = db.query(OrganizationRole).filter(
                OrganizationRole.id == role_id,
                OrganizationRole.organization_id == organization_id
            ).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role not found"
                )

        # Create organization membership
        org_user = OrganizationUser(
            organization_id=organization_id,
            user_id=user_id,
            role_id=role_id,
            status=OrganizationUserStatus.ACTIVE.value,
            invited_by=invited_by,
            joined_at=datetime.now(timezone.utc)
        )
        db.add(org_user)

        # Update user's primary organization if not set
        if not user.organization_id:
            user.organization_id = organization_id

        db.commit()
        db.refresh(org_user)
        return org_user

    def remove_member(
        self,
        db: Session,
        organization_id: str,
        user_id: str
    ) -> None:
        """
        Remove a user from an organization.

        Args:
            db: Database session
            organization_id: Organization UUID
            user_id: User UUID to remove
        """
        # Verify organization exists
        self.get_organization(db, organization_id)

        # Find and remove membership
        org_user = db.query(OrganizationUser).filter(
            OrganizationUser.organization_id == organization_id,
            OrganizationUser.user_id == user_id
        ).first()
        if not org_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this organization"
            )

        db.delete(org_user)
        db.commit()

    def is_slug_available(self, db: Session, slug: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if a slug is available.

        Args:
            db: Database session
            slug: Slug to check
            exclude_id: Optional organization ID to exclude from check (for updates)

        Returns:
            True if slug is available, False otherwise
        """
        query = db.query(Organization).filter(Organization.slug == slug)
        if exclude_id:
            query = query.filter(Organization.id != exclude_id)
        return query.first() is None

    def _generate_slug(self, name: str) -> str:
        """
        Generate URL-friendly slug from organization name.

        Args:
            name: Organization name

        Returns:
            URL-friendly slug
        """
        # Convert to lowercase and replace spaces with hyphens
        slug = name.lower().strip()
        # Remove special characters except alphanumeric and hyphens
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Replace spaces with hyphens
        slug = re.sub(r'[\s]+', '-', slug)
        # Remove duplicate hyphens
        slug = re.sub(r'-+', '-', slug)
        # Limit length
        slug = slug[:100]

        # If slug is empty after cleaning, use a default
        if not slug:
            slug = f"org-{uuid.uuid4().hex[:8]}"

        return slug

    def _is_valid_hex_color(self, color: str) -> bool:
        """
        Validate hex color format.

        Args:
            color: Color string to validate

        Returns:
            True if valid hex color (#RRGGBB format), False otherwise
        """
        if not color:
            return False
        return bool(re.match(r'^#[0-9A-Fa-f]{6}$', color))


# Singleton instance
organization_service = OrganizationService()
