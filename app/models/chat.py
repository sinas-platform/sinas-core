from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any
import uuid

from .base import Base, uuid_pk, created_at, updated_at


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("groups.id"), index=True)
    assistant_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("assistants.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled_webhooks: Mapped[List[str]] = mapped_column(JSON, default=list)
    enabled_mcp_tools: Mapped[List[str]] = mapped_column(JSON, default=list)
    enabled_assistants: Mapped[List[str]] = mapped_column(JSON, default=list)  # List of assistant IDs
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chats")
    assistant: Mapped[Optional["Assistant"]] = relationship("Assistant", back_populates="chats")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid_pk]
    chat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system, tool
    content: Mapped[Optional[str]] = mapped_column(Text)
    tool_calls: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(255))  # For tool response messages
    enabled_webhooks: Mapped[Optional[List[str]]] = mapped_column(JSON)
    enabled_mcp_tools: Mapped[Optional[List[str]]] = mapped_column(JSON)
    created_at: Mapped[created_at]

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
