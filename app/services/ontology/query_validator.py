"""SQL query validation for ontology concept queries."""
import re
from typing import List, Tuple


class SQLValidator:
    """Validates SQL queries for safety and correctness."""

    # Dangerous SQL keywords that should not be in SELECT queries
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        'INSERT', 'UPDATE', 'GRANT', 'REVOKE', 'EXEC',
        'EXECUTE', 'CALL', 'MERGE', 'REPLACE'
    ]

    # Allowed SQL keywords for read-only queries
    ALLOWED_KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT',
        'INNER', 'OUTER', 'ON', 'AS', 'AND', 'OR', 'NOT',
        'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'ORDER', 'BY',
        'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'DISTINCT',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'WITH', 'CTE'
    ]

    @staticmethod
    def validate(sql_query: str) -> Tuple[bool, List[str]]:
        """
        Validate a SQL query for safety.

        Args:
            sql_query: SQL query string to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not sql_query or not sql_query.strip():
            errors.append("SQL query cannot be empty")
            return False, errors

        # Normalize query for checking
        normalized = sql_query.upper().strip()

        # Check for dangerous keywords
        for keyword in SQLValidator.DANGEROUS_KEYWORDS:
            # Use word boundaries to match whole words only
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, normalized):
                errors.append(f"Dangerous keyword '{keyword}' not allowed in queries")

        # Check if query starts with SELECT or WITH (for CTEs)
        if not (normalized.startswith('SELECT') or normalized.startswith('WITH')):
            errors.append("Query must start with SELECT or WITH (for CTEs)")

        # Check for multiple statements (semicolons not at the end)
        if ';' in sql_query.strip()[:-1]:
            errors.append("Multiple SQL statements not allowed (found semicolon in middle of query)")

        # Check for SQL injection patterns
        injection_patterns = [
            r'--',  # SQL comment
            r'/\*',  # Multi-line comment start
            r'\*/',  # Multi-line comment end
        ]

        for pattern in injection_patterns:
            if re.search(pattern, sql_query):
                errors.append(f"Potentially dangerous pattern '{pattern}' found in query")

        # Check balanced parentheses
        if sql_query.count('(') != sql_query.count(')'):
            errors.append("Unbalanced parentheses in query")

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def validate_and_raise(sql_query: str) -> None:
        """
        Validate SQL query and raise ValueError if invalid.

        Args:
            sql_query: SQL query string to validate

        Raises:
            ValueError: If query is invalid
        """
        is_valid, errors = SQLValidator.validate(sql_query)

        if not is_valid:
            error_msg = "SQL query validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ValueError(error_msg)


# Global validator instance
sql_validator = SQLValidator()
