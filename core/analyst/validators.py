"""
Security validators for SQL queries.
"""

import re
from typing import Tuple
from .config import SecurityConfig


class SQLSecurityValidator:
    """Validates SQL queries for security threats."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
    
    def validate_query(self, sql_query: str) -> Tuple[bool, str]:
        """
        Validate SQL query for security issues.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        query_upper = sql_query.upper()
        
        # Check for dangerous operations
        for op in self.config.dangerous_sql_keywords:
            if re.search(r'\b' + op + r'\b', query_upper):
                return False, f"Security violation: {op} operations are not allowed"
        
        # Check for multiple statements
        if ';' in sql_query and not sql_query.strip().endswith(';'):
            return False, "Security violation: Multiple SQL statements detected"
        
        # Ensure query starts with allowed operation
        query_start = query_upper.strip().split()[0] if query_upper.strip() else ''
        
        if not any(query_start.startswith(allowed) for allowed in self.config.allowed_sql_operations):
            allowed_ops = ', '.join(self.config.allowed_sql_operations)
            return False, f"Security violation: Query must start with {allowed_ops}"
        
        # Check for injection patterns
        for pattern in self.config.injection_patterns:
            if re.search(pattern, sql_query):
                return False, "Security violation: Potentially malicious SQL pattern detected"
        
        return True, ""
    
    def sanitize_query(self, query: str) -> str:
        """Clean and sanitize SQL query."""
        # Remove markdown formatting
        query = re.sub(r'^```(?:sql)?', '', query.strip())
        query = re.sub(r'```$', '', query)
        return query.strip()
