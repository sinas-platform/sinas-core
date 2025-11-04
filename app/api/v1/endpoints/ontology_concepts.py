"""API endpoints for Concept management."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.core.database import get_db
from app.models import Concept, Group, Property
from app.schemas.ontology import (
    ConceptCreate,
    ConceptUpdate,
    ConceptResponse,
    PropertyResponse,
)
from app.services.ontology.schema_manager import SchemaManager

router = APIRouter(prefix="/ontology/concepts", tags=["Ontology - Concepts"])


@router.post("", response_model=ConceptResponse, status_code=status.HTTP_201_CREATED)
async def create_concept(
    concept: ConceptCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.concepts.create:all")),
):
    """Create a new concept."""
    # Verify group exists
    result = await db.execute(select(Group).where(Group.id == concept.group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group {concept.group_id} not found"
        )

    # Check if concept already exists with same namespace/name in this group
    result = await db.execute(
        select(Concept).where(
            Concept.group_id == concept.group_id,
            Concept.namespace == concept.namespace,
            Concept.name == concept.name,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Concept {concept.namespace}.{concept.name} already exists in this group"
        )

    db_concept = Concept(
        group_id=concept.group_id,
        namespace=concept.namespace,
        name=concept.name,
        display_name=concept.display_name,
        description=concept.description,
        is_self_managed=concept.is_self_managed,
    )

    db.add(db_concept)
    await db.commit()
    await db.refresh(db_concept)

    # If self-managed, create the table structure (initially empty, properties added later)
    if db_concept.is_self_managed:
        schema_manager = SchemaManager(db)
        # Table will be created when first property is added
        # Or we can create it with just id + audit columns
        await schema_manager.create_table(db_concept, [])

    return db_concept


@router.get("", response_model=List[ConceptResponse])
async def list_concepts(
    group_id: Optional[UUID] = Query(None),
    namespace: Optional[str] = Query(None),
    is_self_managed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.concepts.read:all")),
):
    """List all concepts with optional filters."""
    query = select(Concept)

    if group_id:
        query = query.where(Concept.group_id == group_id)
    if namespace:
        query = query.where(Concept.namespace == namespace)
    if is_self_managed is not None:
        query = query.where(Concept.is_self_managed == is_self_managed)

    result = await db.execute(query.order_by(Concept.namespace, Concept.name))
    concepts = result.scalars().all()

    return concepts


@router.get("/{concept_id}", response_model=ConceptResponse)
async def get_concept(
    concept_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.concepts.read:all")),
):
    """Get a specific concept by ID."""
    result = await db.execute(
        select(Concept).where(Concept.id == concept_id)
    )
    concept = result.scalar_one_or_none()

    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept {concept_id} not found"
        )

    return concept


@router.get("/{concept_id}/properties", response_model=List[PropertyResponse])
async def get_concept_properties(
    concept_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.concepts.read:all")),
):
    """Get all properties for a concept."""
    # Verify concept exists
    result = await db.execute(
        select(Concept).where(Concept.id == concept_id)
    )
    concept = result.scalar_one_or_none()

    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept {concept_id} not found"
        )

    # Get properties
    result = await db.execute(
        select(Property).where(Property.concept_id == concept_id).order_by(Property.name)
    )
    properties = result.scalars().all()

    return properties


@router.put("/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: UUID,
    concept_update: ConceptUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.concepts.update:all")),
):
    """Update a concept (only display_name and description can be changed)."""
    result = await db.execute(
        select(Concept).where(Concept.id == concept_id)
    )
    concept = result.scalar_one_or_none()

    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept {concept_id} not found"
        )

    # Update fields
    update_data = concept_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(concept, field, value)

    await db.commit()
    await db.refresh(concept)

    return concept


@router.delete("/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concept(
    concept_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.concepts.delete:all")),
):
    """Delete a concept and all related data."""
    result = await db.execute(
        select(Concept).where(Concept.id == concept_id)
    )
    concept = result.scalar_one_or_none()

    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept {concept_id} not found"
        )

    # If self-managed, drop the table
    if concept.is_self_managed:
        schema_manager = SchemaManager(db)
        await schema_manager.drop_table(concept)

    # TODO: If synced, drop the synced table

    await db.delete(concept)
    await db.commit()
