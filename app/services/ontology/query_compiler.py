"""Query compiler for ontology endpoints."""
from typing import Dict, Any, List, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Endpoint,
    EndpointProperty,
    EndpointFilter,
    EndpointOrder,
    EndpointJoin,
    Concept,
    ConceptQuery,
    Property,
    Relationship,
    FilterOperator,
)


class QueryCompiler:
    """Compiles endpoint configurations into executable SQL queries."""

    def __init__(self, db: AsyncSession, endpoint: Endpoint):
        self.db = db
        self.endpoint = endpoint
        self.compiled_sql = None
        self.params = {}

    async def compile(self, request_params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Compile endpoint configuration into SQL query.

        Args:
            request_params: Query parameters from the request

        Returns:
            Tuple of (compiled_sql, params_dict)
        """
        # Get the subject concept and its query
        subject_concept = self.endpoint.subject_concept

        result = await self.db.execute(
            select(ConceptQuery).where(ConceptQuery.concept_id == subject_concept.id)
        )
        concept_query = result.scalar_one_or_none()

        if not concept_query:
            raise ValueError(f"No query defined for concept {subject_concept.name}")

        if not concept_query.sql_text:
            raise ValueError(f"Concept {subject_concept.name} has no SQL query (might be self-managed)")

        # Build base CTE
        base_query = f"WITH base_query AS ({concept_query.sql_text})"

        # Compile joins
        joins = await self._compile_joins()

        # Compile selected properties
        selected_properties = await self._compile_properties()

        # Compile filters
        filters, filter_params = await self._compile_filters(request_params)
        self.params.update(filter_params)

        # Compile ordering
        order_by = await self._compile_order()

        # Get limit
        limit = request_params.get('limit', self.endpoint.limit_default)

        # Build final query
        final_query = f"""
        {base_query}
        {joins}
        SELECT {selected_properties}
        FROM base_query
        {filters}
        {order_by}
        LIMIT {limit}
        """

        self.compiled_sql = final_query.strip()
        return self.compiled_sql, self.params

    async def _compile_joins(self) -> str:
        """Compile JOIN clauses from endpoint join configuration."""
        result = await self.db.execute(
            select(EndpointJoin)
            .where(EndpointJoin.endpoint_id == self.endpoint.id)
        )
        endpoint_joins = result.scalars().all()

        if not endpoint_joins:
            return ""

        join_clauses = []
        for idx, ej in enumerate(endpoint_joins):
            # Get the relationship
            result = await self.db.execute(
                select(Relationship).where(Relationship.id == ej.relationship_id)
            )
            relationship = result.scalar_one_or_none()

            if not relationship:
                continue

            # Get target concept
            target_concept = relationship.to_concept

            # Get target concept query
            result = await self.db.execute(
                select(ConceptQuery).where(ConceptQuery.concept_id == target_concept.id)
            )
            target_query = result.scalar_one_or_none()

            if not target_query or not target_query.sql_text:
                continue

            alias = f"joined_{idx}"
            join_cte = f", {alias} AS ({target_query.sql_text})"
            join_clauses.append(join_cte)

        return "".join(join_clauses)

    async def _compile_properties(self) -> str:
        """Compile SELECT clause from endpoint property configuration."""
        result = await self.db.execute(
            select(EndpointProperty)
            .where(
                EndpointProperty.endpoint_id == self.endpoint.id,
                EndpointProperty.include == True
            )
        )
        endpoint_properties = result.scalars().all()

        if not endpoint_properties:
            return "*"

        property_list = []
        for ep in endpoint_properties:
            # Get the property
            result = await self.db.execute(
                select(Property).where(Property.id == ep.property_id)
            )
            property_obj = result.scalar_one_or_none()

            if not property_obj:
                continue

            # Build property expression
            if ep.aggregation:
                property_expr = f"{ep.aggregation}({property_obj.name})"
            else:
                property_expr = property_obj.name

            # Add alias if specified
            if ep.alias:
                property_expr = f"{property_expr} AS {ep.alias}"

            property_list.append(property_expr)

        return ", ".join(property_list) if property_list else "*"

    async def _compile_filters(self, request_params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Compile WHERE clause from endpoint filter configuration."""
        result = await self.db.execute(
            select(EndpointFilter)
            .where(EndpointFilter.endpoint_id == self.endpoint.id)
        )
        endpoint_filters = result.scalars().all()

        if not endpoint_filters:
            return "", {}

        where_clauses = []
        params = {}

        for ef in endpoint_filters:
            param_value = request_params.get(ef.param_name, ef.default_value)

            # Check required parameters
            if ef.required and param_value is None:
                raise ValueError(f"Required parameter {ef.param_name} not provided")

            if param_value is None:
                continue

            # Get the property
            result = await self.db.execute(
                select(Property).where(Property.id == ef.property_id)
            )
            property_obj = result.scalar_one_or_none()

            if not property_obj:
                continue

            # Build filter clause based on operator
            op_value = ef.op.value if hasattr(ef.op, 'value') else ef.op

            if ef.op == FilterOperator.IN:
                # Handle IN operator
                if isinstance(param_value, str):
                    param_value = param_value.split(',')
                placeholders = [f":param_{ef.param_name}_{i}" for i in range(len(param_value))]
                where_clauses.append(f"{property_obj.name} {op_value} ({', '.join(placeholders)})")
                for i, val in enumerate(param_value):
                    params[f"param_{ef.param_name}_{i}"] = val

            elif ef.op == FilterOperator.NOT_IN:
                # Handle NOT IN operator
                if isinstance(param_value, str):
                    param_value = param_value.split(',')
                placeholders = [f":param_{ef.param_name}_{i}" for i in range(len(param_value))]
                where_clauses.append(f"{property_obj.name} {op_value} ({', '.join(placeholders)})")
                for i, val in enumerate(param_value):
                    params[f"param_{ef.param_name}_{i}"] = val

            elif ef.op == FilterOperator.BETWEEN:
                # Handle BETWEEN operator
                if isinstance(param_value, str):
                    values = param_value.split(',')
                    if len(values) != 2:
                        raise ValueError(f"BETWEEN operator requires exactly 2 values for {ef.param_name}")
                    where_clauses.append(f"{property_obj.name} {op_value} :param_{ef.param_name}_0 AND :param_{ef.param_name}_1")
                    params[f"param_{ef.param_name}_0"] = values[0]
                    params[f"param_{ef.param_name}_1"] = values[1]

            elif ef.op in [FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL]:
                # These operators don't need parameters
                where_clauses.append(f"{property_obj.name} {op_value}")

            else:
                # Standard comparison operators
                where_clauses.append(f"{property_obj.name} {op_value} :param_{ef.param_name}")
                params[f"param_{ef.param_name}"] = param_value

        if where_clauses:
            return f"WHERE {' AND '.join(where_clauses)}", params

        return "", {}

    async def _compile_order(self) -> str:
        """Compile ORDER BY clause from endpoint order configuration."""
        result = await self.db.execute(
            select(EndpointOrder)
            .where(EndpointOrder.endpoint_id == self.endpoint.id)
            .order_by(EndpointOrder.priority)
        )
        endpoint_orders = result.scalars().all()

        if not endpoint_orders:
            return ""

        order_clauses = []
        for eo in endpoint_orders:
            # Get the property
            result = await self.db.execute(
                select(Property).where(Property.id == eo.property_id)
            )
            property_obj = result.scalar_one_or_none()

            if not property_obj:
                continue

            order_clauses.append(f"{property_obj.name} {eo.direction.value}")

        if order_clauses:
            return f"ORDER BY {', '.join(order_clauses)}"

        return ""
