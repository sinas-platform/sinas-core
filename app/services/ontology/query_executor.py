"""Query executor for running SQL against data sources."""
from typing import Dict, Any, List
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.models import DataSource
from app.core.encryption import encryption_service


class QueryExecutor:
    """Executes SQL queries against configured data sources."""

    def __init__(self, data_source: DataSource):
        self.data_source = data_source
        self.engine: Engine = None

    def connect(self):
        """Create database connection engine."""
        # Decrypt conn_string before use
        conn_string = encryption_service.decrypt(self.data_source.conn_string)

        # Create engine based on data source type
        if self.data_source.type == "postgres":
            self.engine = create_engine(
                conn_string,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        elif self.data_source.type == "snowflake":
            # Snowflake specific configuration
            self.engine = create_engine(
                conn_string,
                pool_pre_ping=True,
            )
        elif self.data_source.type == "bigquery":
            # BigQuery specific configuration
            self.engine = create_engine(
                conn_string,
                pool_pre_ping=True,
            )
        else:
            raise ValueError(f"Unsupported data source type: {self.data_source.type}")

    def execute(self, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            sql: SQL query to execute
            params: Query parameters

        Returns:
            List of row dictionaries
        """
        if not self.engine:
            self.connect()

        with self.engine.connect() as connection:
            result = connection.execute(text(sql), params)

            rows = []
            for row in result:
                rows.append(dict(row._mapping))

            return rows

    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
