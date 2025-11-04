"""Executions API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user_with_permissions, require_permission
from app.models.execution import Execution, StepExecution, ExecutionStatus
from app.schemas import ExecutionResponse, StepExecutionResponse

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("", response_model=List[ExecutionResponse])
async def list_executions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    function_name: Optional[str] = None,
    status: Optional[ExecutionStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user_data = Depends(get_current_user_with_permissions)
):
    """List executions (own and group-accessible)."""
    user_id, permissions = current_user_data

    # Build query based on permissions
    if permissions.get("sinas.executions.read:all"):
        query = select(Execution)
    else:
        query = select(Execution).where(Execution.user_id == user_id)

    if function_name:
        query = query.where(Execution.function_name == function_name)
    if status:
        query = query.where(Execution.status == status)

    query = query.order_by(Execution.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    executions = result.scalars().all()

    return executions


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_data = Depends(get_current_user_with_permissions)
):
    """Get a specific execution."""
    user_id, permissions = current_user_data

    result = await db.execute(
        select(Execution).where(Execution.execution_id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Check permissions
    if not permissions.get("sinas.executions.read:all"):
        if execution.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this execution")

    return execution


@router.get("/{execution_id}/steps", response_model=List[StepExecutionResponse])
async def get_execution_steps(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_data = Depends(get_current_user_with_permissions)
):
    """Get all steps for an execution."""
    user_id, permissions = current_user_data

    # First check if execution exists and user has access
    result = await db.execute(
        select(Execution).where(Execution.execution_id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if not permissions.get("sinas.executions.read:all"):
        if execution.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this execution")

    # Get steps
    result = await db.execute(
        select(StepExecution)
        .where(StepExecution.execution_id == execution_id)
        .order_by(StepExecution.started_at)
    )
    steps = result.scalars().all()

    return steps
