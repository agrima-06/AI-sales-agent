"""
Identity & Access Domain Models
===============================

Domain: IAM (Identity, RBAC, and Audit)

Entities:
  - User            : Platform users (Admin, Warehouse Staff, Support).
  - Role            : A named group of capabilities (e.g., 'warehouse_manager').
  - Permission      : A fine-grained capability (e.g., 'orders:write', 'inventory:delete').
  - UserRole        : Junction table assigning multiple roles to a user.
  - RolePermission  : Junction table assigning multiple permissions to a role.
  - AuditLog        : Immutable ledger of who did what and when.
  - RefreshToken    : Tracked tokens for secure session rotation.
  - UserSession     : Active session tracking for security and forced logouts.

Design Decisions:
  - RBAC (Role-Based Access Control): We use a standard 3-tier RBAC model. Users are assigned
    Roles, and Roles are composed of Permissions. The application code will always check
    permissions (`has_permission('orders:write')`) rather than checking roles (`is_admin()`),
    ensuring maximum flexibility if roles change in the future.
  - Multi-Company: The User model includes an optional `tenant_id` to support future multi-tenant
    or multi-company scaling.
  - Security Tracking: The `User` model tracks `failed_login_attempts` to support account locking,
    and `password_changed_at` to invalidate old sessions.
  - Audit Logging: `AuditLog` captures JSONB payloads of `old_values` and `new_values`. This is
    critical for enterprise compliance (e.g., SOC2) to prove who changed an order or credit limit.

Relationships:
  User 1─── N UserRole N ───1 Role
  Role 1─── N RolePermission N ───1 Permission
  User 1─── N UserSession
  User 1─── N RefreshToken
  User 1─── N AuditLog
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase


# -----------------------------------------------------------------------------
# Core Identity
# -----------------------------------------------------------------------------


class User(TimestampedBase):
    """
    Platform user (System Administrators, Finance, Warehouse Staff, etc.).
    Note: Dealers are a separate domain. A dealer might have a User account
    linked to them for a web portal later, but 'User' here represents a login identity.
    """

    __tablename__ = "users"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Support for future multi-company/multi-tenant architecture",
    )

    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Pending",
        index=True,
        comment="Active, Disabled, Locked, Pending",
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Bypasses all RBAC checks"
    )

    # Security & Tracking
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('Active', 'Disabled', 'Locked', 'Pending')",
            name="ck_user_status",
        ),
    )


# -----------------------------------------------------------------------------
# RBAC (Role-Based Access Control)
# -----------------------------------------------------------------------------


class Role(TimestampedBase):
    """
    A named group of capabilities (e.g., 'Finance Manager').
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="System roles cannot be modified or deleted via UI",
    )

    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(TimestampedBase):
    """
    Fine-grained capability.
    Format is typically resource:action (e.g., 'orders:write', 'inventory:read').
    """

    __tablename__ = "permissions"

    resource: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
    )


class UserRole(TimestampedBase):
    """Junction mapping Users to Roles."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class RolePermission(TimestampedBase):
    """Junction mapping Roles to Permissions."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="role_permissions"
    )

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )


# -----------------------------------------------------------------------------
# Security & Sessions
# -----------------------------------------------------------------------------


class UserSession(TimestampedBase):
    """
    Tracks active user sessions.
    Allows admins to forcefully invalidate specific sessions (e.g., log out all devices).
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_token: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class RefreshToken(TimestampedBase):
    """
    Long-lived tokens for requesting new short-lived access tokens.
    Supports token revocation and rotation.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


# -----------------------------------------------------------------------------
# Audit
# -----------------------------------------------------------------------------


class AuditLog(TimestampedBase):
    """
    Immutable ledger of system changes for enterprise compliance.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who made the change. NULL if system/AI action.",
    )

    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="CREATE, UPDATE, DELETE, LOGIN"
    )
    resource_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="Table or entity name"
    )
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
