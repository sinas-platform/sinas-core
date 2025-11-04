"""User schemas."""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserWithGroupsResponse(UserResponse):
    groups: List[str]  # List of group names


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
