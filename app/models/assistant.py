from sqlalchemy import String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any
import uuid

from .base import Base, uuid_pk, created_at, updated_at


class Assistant(Base):
    __tablename__ = "assistants"

    id: Mapped[uuid_pk]
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), index=True
    )  # NULL = workspace-wide
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("groups.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    enabled_webhooks: Mapped[List[str]] = mapped_column(JSON, default=list)
    enabled_mcp_tools: Mapped[List[str]] = mapped_column(JSON, default=list)
    webhook_parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    mcp_tool_parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="assistants")
    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="assistant")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("groups.id"), index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memories")

    __table_args__ = (
        {"schema": None},  # Can add unique constraint here if needed
    )
