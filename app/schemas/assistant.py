"""Assistant and memory schemas."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class AssistantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    group_id: Optional[uuid.UUID] = None
    enabled_webhooks: Optional[List[str]] = None
    enabled_mcp_tools: Optional[List[str]] = None
    webhook_parameters: Optional[Dict[str, Any]] = None
    mcp_tool_parameters: Optional[Dict[str, Any]] = None


class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    enabled_webhooks: Optional[List[str]] = None
    enabled_mcp_tools: Optional[List[str]] = None
    webhook_parameters: Optional[Dict[str, Any]] = None
    mcp_tool_parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AssistantResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    group_id: Optional[uuid.UUID]
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    enabled_webhooks: List[str]
    enabled_mcp_tools: List[str]
    webhook_parameters: Dict[str, Any]
    mcp_tool_parameters: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemoryCreate(BaseModel):
    key: str
    value: str
    group_id: Optional[uuid.UUID] = None


class MemoryUpdate(BaseModel):
    value: str


class MemoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    key: str
    value: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
