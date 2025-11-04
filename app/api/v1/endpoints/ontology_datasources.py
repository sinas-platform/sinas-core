"""API endpoints for DataSource management."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission, get_current_user_with_permissions
from app.core.database import get_db
from app.core.permissions import check_permission
from app.core.encryption import encryption_service
from app.models import DataSource, Group
from app.schemas.ontology import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
)

router = APIRouter(prefix="/ontology/datasources", tags=["Ontology - DataSources"])


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_datasource(
    datasource: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.datasources.create:all")),
):
    """Create a new data source."""
    # Verify group exists
    result = await db.execute(select(Group).where(Group.id == datasource.group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group {datasource.group_id} not found"
        )

    # Encrypt conn_string before storing
    encrypted_conn_string = encryption_service.encrypt(datasource.conn_string)

    db_datasource = DataSource(
        group_id=datasource.group_id,
        name=datasource.name,
        type=datasource.type,
        conn_string=encrypted_conn_string,
        default_database=datasource.default_database,
        default_schema=datasource.default_schema,
    )

    db.add(db_datasource)
    await db.commit()
    await db.refresh(db_datasource)

    return db_datasource


@router.get("", response_model=List[DataSourceResponse])
async def list_datasources(
    group_id: UUID = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.datasources.read:all")),
):
    """List all data sources, optionally filtered by group."""
    query = select(DataSource)

    if group_id:
        query = query.where(DataSource.group_id == group_id)

    result = await db.execute(query.order_by(DataSource.created_at.desc()))
    datasources = result.scalars().all()

    return datasources


@router.get("/{datasource_id}", response_model=DataSourceResponse)
async def get_datasource(
    datasource_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.datasources.read:all")),
):
    """Get a specific data source by ID."""
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataSource {datasource_id} not found"
        )

    return datasource


@router.put("/{datasource_id}", response_model=DataSourceResponse)
async def update_datasource(
    datasource_id: UUID,
    datasource_update: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.datasources.update:all")),
):
    """Update a data source."""
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataSource {datasource_id} not found"
        )

    # Update fields
    update_data = datasource_update.model_dump(exclude_unset=True)

    # Encrypt conn_string if provided
    if 'conn_string' in update_data:
        update_data['conn_string'] = encryption_service.encrypt(update_data['conn_string'])

    for field, value in update_data.items():
        setattr(datasource, field, value)

    await db.commit()
    await db.refresh(datasource)

    return datasource


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(
    datasource_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.datasources.delete:all")),
):
    """Delete a data source."""
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataSource {datasource_id} not found"
        )

    await db.delete(datasource)
    await db.commit()
