"""API endpoints for Property and Relationship management."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.core.database import get_db
from app.models import Property, Concept, Relationship
from app.schemas.ontology import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    RelationshipCreate,
    RelationshipUpdate,
    RelationshipResponse,
)
from app.services.ontology.schema_manager import SchemaManager

property_router = APIRouter(prefix="/ontology/properties", tags=["Ontology - Properties"])
relationship_router = APIRouter(prefix="/ontology/relationships", tags=["Ontology - Relationships"])


# ============================================================================
# Property Endpoints
# ============================================================================

@property_router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.properties.create:all")),
):
    """Create a new property for a concept."""
    # Verify concept exists
    result = await db.execute(
        select(Concept).where(Concept.id == property_data.concept_id)
    )
    concept = result.scalar_one_or_none()
    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept {property_data.concept_id} not found"
        )

    # Check if property already exists with same name in this concept
    result = await db.execute(
        select(Property).where(
            Property.concept_id == property_data.concept_id,
            Property.name == property_data.name,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Property {property_data.name} already exists for this concept"
        )

    db_property = Property(
        concept_id=property_data.concept_id,
        name=property_data.name,
        display_name=property_data.display_name,
        description=property_data.description,
        data_type=property_data.data_type,
        is_identifier=property_data.is_identifier,
        is_required=property_data.is_required,
        default_value=property_data.default_value,
    )

    db.add(db_property)
    await db.commit()
    await db.refresh(db_property)

    # If concept is self-managed, alter table to add column
    if concept.is_self_managed:
        schema_manager = SchemaManager(db)
        await schema_manager.add_column(concept, db_property)

    return db_property


@property_router.get("", response_model=List[PropertyResponse])
async def list_properties(
    concept_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.properties.read:all")),
):
    """List all properties, optionally filtered by concept."""
    query = select(Property)

    if concept_id:
        query = query.where(Property.concept_id == concept_id)

    result = await db.execute(query.order_by(Property.name))
    properties = result.scalars().all()

    return properties


@property_router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.properties.read:all")),
):
    """Get a specific property by ID."""
    result = await db.execute(
        select(Property).where(Property.id == property_id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found"
        )

    return property_obj


@property_router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_update: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.properties.update:all")),
):
    """Update a property."""
    result = await db.execute(
        select(Property).where(Property.id == property_id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found"
        )

    # Get concept to check if it's self-managed
    result = await db.execute(
        select(Concept).where(Concept.id == property_obj.concept_id)
    )
    concept = result.scalar_one_or_none()

    # Update fields
    update_data = property_update.model_dump(exclude_unset=True)
    old_property = Property(
        id=property_obj.id,
        concept_id=property_obj.concept_id,
        name=property_obj.name,
        data_type=property_obj.data_type,
        is_identifier=property_obj.is_identifier,
        is_required=property_obj.is_required,
        default_value=property_obj.default_value,
    )

    for field, value in update_data.items():
        setattr(property_obj, field, value)

    await db.commit()
    await db.refresh(property_obj)

    # If concept is self-managed and data_type changed, migrate column
    if concept and concept.is_self_managed and 'data_type' in update_data:
        schema_manager = SchemaManager(db)
        await schema_manager.migrate_column(concept, old_property, property_obj)

    return property_obj


@property_router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.properties.delete:all")),
):
    """Delete a property."""
    result = await db.execute(
        select(Property).where(Property.id == property_id)
    )
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found"
        )

    # Get concept to check if it's self-managed
    result = await db.execute(
        select(Concept).where(Concept.id == property_obj.concept_id)
    )
    concept = result.scalar_one_or_none()

    # If concept is self-managed, rename column to deleted_columnname_timestamp
    if concept and concept.is_self_managed:
        schema_manager = SchemaManager(db)
        await schema_manager.mark_column_deleted(concept, property_obj)

    await db.delete(property_obj)
    await db.commit()


# ============================================================================
# Relationship Endpoints
# ============================================================================

@relationship_router.post("", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    relationship: RelationshipCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.relationships.create:all")),
):
    """Create a new relationship between concepts."""
    # Verify concepts exist
    result = await db.execute(
        select(Concept).where(
            Concept.id.in_([relationship.from_concept_id, relationship.to_concept_id])
        )
    )
    concepts = result.scalars().all()
    if len(concepts) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both concepts not found"
        )

    # Verify properties exist
    result = await db.execute(
        select(Property).where(
            Property.id.in_([relationship.from_property_id, relationship.to_property_id])
        )
    )
    properties = result.scalars().all()
    if len(properties) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both properties not found"
        )

    db_relationship = Relationship(
        from_concept_id=relationship.from_concept_id,
        to_concept_id=relationship.to_concept_id,
        name=relationship.name,
        cardinality=relationship.cardinality,
        from_property_id=relationship.from_property_id,
        to_property_id=relationship.to_property_id,
        description=relationship.description,
    )

    db.add(db_relationship)
    await db.commit()
    await db.refresh(db_relationship)

    return db_relationship


@relationship_router.get("", response_model=List[RelationshipResponse])
async def list_relationships(
    concept_id: Optional[UUID] = Query(None, description="Filter by concept (from or to)"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.relationships.read:all")),
):
    """List all relationships, optionally filtered by concept."""
    query = select(Relationship)

    if concept_id:
        query = query.where(
            (Relationship.from_concept_id == concept_id) |
            (Relationship.to_concept_id == concept_id)
        )

    result = await db.execute(query.order_by(Relationship.name))
    relationships = result.scalars().all()

    return relationships


@relationship_router.get("/{relationship_id}", response_model=RelationshipResponse)
async def get_relationship(
    relationship_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.relationships.read:all")),
):
    """Get a specific relationship by ID."""
    result = await db.execute(
        select(Relationship).where(Relationship.id == relationship_id)
    )
    relationship = result.scalar_one_or_none()

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found"
        )

    return relationship


@relationship_router.put("/{relationship_id}", response_model=RelationshipResponse)
async def update_relationship(
    relationship_id: UUID,
    relationship_update: RelationshipUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.relationships.update:all")),
):
    """Update a relationship."""
    result = await db.execute(
        select(Relationship).where(Relationship.id == relationship_id)
    )
    relationship = result.scalar_one_or_none()

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found"
        )

    # Update fields
    update_data = relationship_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(relationship, field, value)

    await db.commit()
    await db.refresh(relationship)

    return relationship


@relationship_router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(
    relationship_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.relationships.delete:all")),
):
    """Delete a relationship."""
    result = await db.execute(
        select(Relationship).where(Relationship.id == relationship_id)
    )
    relationship = result.scalar_one_or_none()

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found"
        )

    await db.delete(relationship)
    await db.commit()
