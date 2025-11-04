"""Data synchronization service for synced concepts."""
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Concept, ConceptQuery, Property
from app.services.ontology.schema_manager import SchemaManager
from app.services.ontology.query_executor import QueryExecutor


class SyncService:
    """Handles syncing data from external sources to local tables."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_sync_table_name(concept: Concept) -> str:
        """
        Generate table name for synced concept data.

        Format: ontology_sync_{namespace}_{name}
        """
        return f"ontology_sync_{concept.namespace}_{concept.name}"

    async def create_sync_table(
        self,
        concept: Concept,
        properties: List[Property]
    ) -> None:
        """
        Create a table for synced concept data.

        Args:
            concept: The concept to sync
            properties: Properties defining the schema
        """
        table_name = self.get_sync_table_name(concept)

        # Check if table already exists
        schema_manager = SchemaManager(self.db)
        if await schema_manager.table_exists(table_name):
            # Table exists, we'll just truncate and refill
            return

        # Build column definitions
        columns = ["id UUID PRIMARY KEY"]

        for prop in properties:
            pg_type = schema_manager.get_pg_type(prop.data_type)
            column_def = f"{prop.name} {pg_type}"

            if prop.is_required:
                column_def += " NOT NULL"

            columns.append(column_def)

        # Add audit columns
        columns.append("synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")

        # Create table
        create_sql = f"""
            CREATE TABLE {table_name} (
                {', '.join(columns)}
            )
        """

        await self.db.execute(text(create_sql))

        # Create indexes for identifier properties
        for prop in properties:
            if prop.is_identifier:
                index_name = f"idx_{table_name}_{prop.name}"
                index_sql = f"CREATE INDEX {index_name} ON {table_name} ({prop.name})"
                await self.db.execute(text(index_sql))

        await self.db.commit()

    async def sync_concept(self, concept_id: UUID) -> Dict[str, Any]:
        """
        Perform a sync operation for a concept.

        Args:
            concept_id: UUID of the concept to sync

        Returns:
            Dict with sync results (row_count, duration, etc.)
        """
        start_time = datetime.utcnow()

        # Get concept
        result = await self.db.execute(
            select(Concept).where(Concept.id == concept_id)
        )
        concept = result.scalar_one_or_none()

        if not concept:
            raise ValueError(f"Concept {concept_id} not found")

        # Get concept query
        result = await self.db.execute(
            select(ConceptQuery).where(ConceptQuery.concept_id == concept_id)
        )
        concept_query = result.scalar_one_or_none()

        if not concept_query:
            raise ValueError(f"No query defined for concept {concept_id}")

        if not concept_query.sync_enabled:
            raise ValueError(f"Sync not enabled for concept {concept_id}")

        if not concept_query.data_source:
            raise ValueError(f"No data source configured for concept {concept_id}")

        if not concept_query.sql_text:
            raise ValueError(f"No SQL query defined for concept {concept_id}")

        # Get properties
        result = await self.db.execute(
            select(Property).where(Property.concept_id == concept_id)
        )
        properties = result.scalars().all()

        # Ensure sync table exists
        await self.create_sync_table(concept, properties)

        # Execute query on external source
        executor = QueryExecutor(concept_query.data_source)

        try:
            with executor:
                # Execute the concept query
                rows = executor.execute(concept_query.sql_text, {})

            # Get sync table name
            sync_table_name = self.get_sync_table_name(concept)

            # Truncate existing data
            truncate_sql = f"TRUNCATE TABLE {sync_table_name}"
            await self.db.execute(text(truncate_sql))

            # Insert new data
            if rows:
                # Build bulk insert
                row_count = 0
                for row in rows:
                    # Map row data to columns
                    columns = list(row.keys())
                    placeholders = [f":{col}" for col in columns]

                    insert_sql = f"""
                        INSERT INTO {sync_table_name} ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                    """

                    await self.db.execute(text(insert_sql), row)
                    row_count += 1

                await self.db.commit()
            else:
                row_count = 0

            # Update last_synced_at
            concept_query.last_synced_at = datetime.utcnow()
            await self.db.commit()

            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            return {
                "concept_id": str(concept_id),
                "concept_name": f"{concept.namespace}.{concept.name}",
                "status": "success",
                "row_count": row_count,
                "duration_seconds": duration_seconds,
                "synced_at": concept_query.last_synced_at.isoformat()
            }

        except Exception as e:
            await self.db.rollback()
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            return {
                "concept_id": str(concept_id),
                "concept_name": f"{concept.namespace}.{concept.name}",
                "status": "failed",
                "error": str(e),
                "duration_seconds": duration_seconds
            }

    async def drop_sync_table(self, concept: Concept) -> None:
        """
        Drop the sync table for a concept.

        Args:
            concept: The concept whose sync table to drop
        """
        table_name = self.get_sync_table_name(concept)

        drop_sql = f"DROP TABLE IF EXISTS {table_name} CASCADE"
        await self.db.execute(text(drop_sql))
        await self.db.commit()


def _parse_cron_expression(cron_expr: str) -> dict:
    """Parse cron expression into APScheduler cron trigger parameters."""
    parts = cron_expr.split()

    if len(parts) != 5:
        raise ValueError("Cron expression must have 5 parts: minute hour day month day_of_week")

    return {
        'minute': parts[0],
        'hour': parts[1],
        'day': parts[2],
        'month': parts[3],
        'day_of_week': parts[4]
    }


async def schedule_sync_job(
    db: AsyncSession,
    concept_query: ConceptQuery
) -> None:
    """
    Schedule a sync job using APScheduler.

    Args:
        db: Database session
        concept_query: ConceptQuery with sync configuration
    """
    if not concept_query.sync_enabled or not concept_query.sync_schedule:
        return

    # Import scheduler
    from app.services.scheduler import scheduler

    job_id = f"ontology_sync_{concept_query.concept_id}"

    try:
        # Parse cron expression
        cron_params = _parse_cron_expression(concept_query.sync_schedule)

        # Add job to scheduler
        scheduler.scheduler.add_job(
            func=sync_concept_job,
            trigger='cron',
            args=[str(concept_query.concept_id)],
            id=job_id,
            name=f"Sync concept {concept_query.concept_id}",
            **cron_params,
            replace_existing=True
        )

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to schedule sync job for concept {concept_query.concept_id}: {e}")


async def remove_sync_job(concept_id: UUID) -> None:
    """
    Remove a scheduled sync job.

    Args:
        concept_id: UUID of the concept
    """
    from app.services.scheduler import scheduler

    job_id = f"ontology_sync_{concept_id}"

    try:
        scheduler.scheduler.remove_job(job_id)
    except Exception:
        # Job might not exist, that's okay
        pass


async def sync_concept_job(concept_id: str) -> None:
    """
    Background job function for syncing a concept.

    Args:
        concept_id: UUID string of the concept to sync
    """
    # This would be called by APScheduler
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        sync_service = SyncService(db)
        result = await sync_service.sync_concept(UUID(concept_id))

        # Log result
        print(f"Sync completed: {result}")
