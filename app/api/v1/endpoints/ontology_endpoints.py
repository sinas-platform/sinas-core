"""API endpoints for Endpoint configuration management."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query as QueryParam
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.core.database import get_db
from app.models import (
    Endpoint,
    EndpointProperty,
    EndpointFilter,
    EndpointOrder,
    EndpointJoin,
    Concept,
    Property,
    Relationship,
)
from app.schemas.ontology import (
    EndpointCreate,
    EndpointUpdate,
    EndpointResponse,
    EndpointPropertyCreate,
    EndpointPropertyResponse,
    EndpointFilterCreate,
    EndpointFilterResponse,
    EndpointOrderCreate,
    EndpointOrderResponse,
    EndpointJoinCreate,
    EndpointJoinResponse,
)

router = APIRouter(prefix="/ontology/endpoints", tags=["Ontology - Endpoints"])


# ============================================================================
# Endpoint CRUD
# ============================================================================

@router.post("", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    endpoint: EndpointCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.create:all")),
):
    """Create a new API endpoint configuration."""
    # Verify concept exists
    result = await db.execute(
        select(Concept).where(Concept.id == endpoint.subject_concept_id)
    )
    concept = result.scalar_one_or_none()
    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept {endpoint.subject_concept_id} not found"
        )

    # Check route uniqueness
    result = await db.execute(
        select(Endpoint).where(Endpoint.route == endpoint.route)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Route {endpoint.route} already exists"
        )

    db_endpoint = Endpoint(
        name=endpoint.name,
        route=endpoint.route,
        subject_concept_id=endpoint.subject_concept_id,
        response_format=endpoint.response_format,
        enabled=endpoint.enabled,
        description=endpoint.description,
        limit_default=endpoint.limit_default,
    )

    db.add(db_endpoint)
    await db.commit()
    await db.refresh(db_endpoint)

    return db_endpoint


@router.get("", response_model=List[EndpointResponse])
async def list_endpoints(
    enabled: Optional[bool] = QueryParam(None),
    concept_id: Optional[UUID] = QueryParam(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.read:all")),
):
    """List all endpoints with optional filters."""
    query = select(Endpoint)

    if enabled is not None:
        query = query.where(Endpoint.enabled == enabled)
    if concept_id:
        query = query.where(Endpoint.subject_concept_id == concept_id)

    result = await db.execute(query.order_by(Endpoint.name))
    endpoints = result.scalars().all()

    return endpoints


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.read:all")),
):
    """Get a specific endpoint by ID."""
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    return endpoint


@router.put("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: UUID,
    endpoint_update: EndpointUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Update an endpoint."""
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    # Check route uniqueness if being updated
    update_data = endpoint_update.model_dump(exclude_unset=True)

    if "route" in update_data:
        result = await db.execute(
            select(Endpoint).where(
                Endpoint.route == update_data["route"],
                Endpoint.id != endpoint_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Route {update_data['route']} already exists"
            )

    for field, value in update_data.items():
        setattr(endpoint, field, value)

    await db.commit()
    await db.refresh(endpoint)

    return endpoint


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.delete:all")),
):
    """Delete an endpoint."""
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    await db.delete(endpoint)
    await db.commit()


# ============================================================================
# Endpoint Properties
# ============================================================================

@router.post("/properties", response_model=EndpointPropertyResponse, status_code=status.HTTP_201_CREATED)
async def add_endpoint_property(
    prop: EndpointPropertyCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Add a property to an endpoint."""
    # Verify endpoint, concept, and property exist
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == prop.endpoint_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    result = await db.execute(
        select(Property).where(Property.id == prop.property_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    db_prop = EndpointProperty(
        endpoint_id=prop.endpoint_id,
        concept_id=prop.concept_id,
        property_id=prop.property_id,
        alias=prop.alias,
        aggregation=prop.aggregation,
        include=prop.include,
    )

    db.add(db_prop)
    await db.commit()
    await db.refresh(db_prop)

    return db_prop


@router.get("/properties", response_model=List[EndpointPropertyResponse])
async def list_endpoint_properties(
    endpoint_id: Optional[UUID] = QueryParam(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.read:all")),
):
    """List endpoint properties."""
    query = select(EndpointProperty)

    if endpoint_id:
        query = query.where(EndpointProperty.endpoint_id == endpoint_id)

    result = await db.execute(query)
    properties = result.scalars().all()

    return properties


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Remove a property from an endpoint."""
    result = await db.execute(
        select(EndpointProperty).where(EndpointProperty.id == property_id)
    )
    prop = result.scalar_one_or_none()

    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint property not found")

    await db.delete(prop)
    await db.commit()


# ============================================================================
# Endpoint Filters
# ============================================================================

@router.post("/filters", response_model=EndpointFilterResponse, status_code=status.HTTP_201_CREATED)
async def add_endpoint_filter(
    filter_data: EndpointFilterCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Add a filter to an endpoint."""
    # Verify endpoint and property exist
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == filter_data.endpoint_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    result = await db.execute(
        select(Property).where(Property.id == filter_data.property_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    db_filter = EndpointFilter(
        endpoint_id=filter_data.endpoint_id,
        property_id=filter_data.property_id,
        op=filter_data.op,
        param_name=filter_data.param_name,
        required=filter_data.required,
        default_value=filter_data.default_value,
    )

    db.add(db_filter)
    await db.commit()
    await db.refresh(db_filter)

    return db_filter


@router.get("/filters", response_model=List[EndpointFilterResponse])
async def list_endpoint_filters(
    endpoint_id: Optional[UUID] = QueryParam(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.read:all")),
):
    """List endpoint filters."""
    query = select(EndpointFilter)

    if endpoint_id:
        query = query.where(EndpointFilter.endpoint_id == endpoint_id)

    result = await db.execute(query)
    filters = result.scalars().all()

    return filters


@router.delete("/filters/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint_filter(
    filter_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Remove a filter from an endpoint."""
    result = await db.execute(
        select(EndpointFilter).where(EndpointFilter.id == filter_id)
    )
    filter_obj = result.scalar_one_or_none()

    if not filter_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint filter not found")

    await db.delete(filter_obj)
    await db.commit()


# ============================================================================
# Endpoint Orders
# ============================================================================

@router.post("/orders", response_model=EndpointOrderResponse, status_code=status.HTTP_201_CREATED)
async def add_endpoint_order(
    order_data: EndpointOrderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Add an order/sort to an endpoint."""
    # Verify endpoint and property exist
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == order_data.endpoint_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    result = await db.execute(
        select(Property).where(Property.id == order_data.property_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    db_order = EndpointOrder(
        endpoint_id=order_data.endpoint_id,
        property_id=order_data.property_id,
        direction=order_data.direction,
        priority=order_data.priority,
    )

    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)

    return db_order


@router.get("/orders", response_model=List[EndpointOrderResponse])
async def list_endpoint_orders(
    endpoint_id: Optional[UUID] = QueryParam(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.read:all")),
):
    """List endpoint orders."""
    query = select(EndpointOrder)

    if endpoint_id:
        query = query.where(EndpointOrder.endpoint_id == endpoint_id)

    result = await db.execute(query.order_by(EndpointOrder.priority))
    orders = result.scalars().all()

    return orders


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Remove an order from an endpoint."""
    result = await db.execute(
        select(EndpointOrder).where(EndpointOrder.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint order not found")

    await db.delete(order)
    await db.commit()


# ============================================================================
# Endpoint Joins
# ============================================================================

@router.post("/joins", response_model=EndpointJoinResponse, status_code=status.HTTP_201_CREATED)
async def add_endpoint_join(
    join_data: EndpointJoinCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Add a join to an endpoint."""
    # Verify endpoint and relationship exist
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == join_data.endpoint_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    result = await db.execute(
        select(Relationship).where(Relationship.id == join_data.relationship_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")

    db_join = EndpointJoin(
        endpoint_id=join_data.endpoint_id,
        relationship_id=join_data.relationship_id,
        join_type=join_data.join_type,
    )

    db.add(db_join)
    await db.commit()
    await db.refresh(db_join)

    return db_join


@router.get("/joins", response_model=List[EndpointJoinResponse])
async def list_endpoint_joins(
    endpoint_id: Optional[UUID] = QueryParam(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.read:all")),
):
    """List endpoint joins."""
    query = select(EndpointJoin)

    if endpoint_id:
        query = query.where(EndpointJoin.endpoint_id == endpoint_id)

    result = await db.execute(query)
    joins = result.scalars().all()

    return joins


@router.delete("/joins/{join_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint_join(
    join_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.endpoints.update:all")),
):
    """Remove a join from an endpoint."""
    result = await db.execute(
        select(EndpointJoin).where(EndpointJoin.id == join_id)
    )
    join = result.scalar_one_or_none()

    if not join:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint join not found")

    await db.delete(join)
    await db.commit()
