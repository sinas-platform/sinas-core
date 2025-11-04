from sqlalchemy import String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Dict, Any

from .base import Base, uuid_pk, created_at, updated_at


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid_pk]
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)  # websocket or http
    api_key: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_connected: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    connection_status: Mapped[str] = mapped_column(
        String(50), default="disconnected", nullable=False
    )  # connected, disconnected, error
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[uuid_pk]
    user_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    chat_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    request_data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    response_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    tokens_prompt: Mapped[Optional[int]] = mapped_column()
    tokens_completion: Mapped[Optional[int]] = mapped_column()
    tokens_total: Mapped[Optional[int]] = mapped_column()
    latency_ms: Mapped[Optional[int]] = mapped_column()
    status_code: Mapped[Optional[int]] = mapped_column()
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[created_at]
