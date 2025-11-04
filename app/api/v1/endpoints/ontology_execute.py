"""API endpoints for executing ontology queries."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.core.database import get_db
from app.models import Endpoint, ConceptQuery
from app.schemas.ontology import QueryExecutionResponse, CompiledQueryResponse
from app.services.ontology import QueryCompiler, QueryExecutor

router = APIRouter(prefix="/ontology/execute", tags=["Ontology - Execution"])


@router.get("/{endpoint_id}", response_model=QueryExecutionResponse)
async def execute_endpoint(
    endpoint_id: UUID,
    request: Request,
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.queries.execute:all")),
):
    """
    Execute a configured endpoint with query parameters.

    Args:
        endpoint_id: UUID of the endpoint to execute
        request: FastAPI request object (for query params)
        limit: Optional limit override
        db: Database session
        user_id: Authenticated user ID

    Returns:
        Query results with count
    """
    # Get endpoint
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    if not endpoint.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint is disabled"
        )

    # Get query parameters from request
    request_params = dict(request.query_params)
    if limit:
        request_params['limit'] = limit

    # Compile the query
    compiler = QueryCompiler(db, endpoint)
    try:
        sql, params = await compiler.compile(request_params)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query compilation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query compilation error: {str(e)}"
        )

    # Get the concept query to find the data source
    result = await db.execute(
        select(ConceptQuery).where(
            ConceptQuery.concept_id == endpoint.subject_concept_id
        )
    )
    concept_query = result.scalar_one_or_none()

    if not concept_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No query defined for endpoint's subject concept"
        )

    if not concept_query.data_source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Concept has no data source configured"
        )

    # Execute the query
    executor = QueryExecutor(concept_query.data_source)

    try:
        with executor:
            results = executor.execute(sql, params)

        return QueryExecutionResponse(
            data=results,
            count=len(results)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@router.get("/compile/{endpoint_id}", response_model=CompiledQueryResponse)
async def compile_endpoint(
    endpoint_id: UUID,
    request: Request,
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_permission("sinas.ontology.queries.read:all")),
):
    """
    Compile an endpoint query without executing (for debugging).

    Args:
        endpoint_id: UUID of the endpoint
        request: FastAPI request object
        limit: Optional limit override
        db: Database session
        user_id: Authenticated user ID

    Returns:
        Compiled SQL and parameters
    """
    # Get endpoint
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {endpoint_id} not found"
        )

    # Get query parameters from request
    request_params = dict(request.query_params)
    if limit:
        request_params['limit'] = limit

    # Compile the query
    compiler = QueryCompiler(db, endpoint)
    try:
        sql, params = await compiler.compile(request_params)
        return CompiledQueryResponse(
            sql=sql,
            params=params
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query compilation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query compilation error: {str(e)}"
        )
