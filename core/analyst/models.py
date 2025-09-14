"""
Data models for the AI Analyst system.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re


class QueryStatus(str, Enum):
    """Status of a database query execution."""
    SUCCESS = "success"
    ERROR = "error"
    RETRY = "retry"


class SQLQuery(BaseModel):
    """Validated SQL Query with security checks."""
    query: str
    is_valid: bool = True
    error_message: Optional[str] = None
    
    @field_validator('query')
    def validate_sql(cls, v):
        """Validate and sanitize SQL query for security."""
        # Clean up the query
        v = v.strip()
        
        # Remove markdown formatting
        v = re.sub(r'^```(?:sql)?', '', v)
        v = re.sub(r'```$', '', v)
        v = v.strip()
        
        # Security: Block dangerous operations
        dangerous_keywords = [
            'DELETE', 'DROP', 'TRUNCATE', 'INSERT', 'UPDATE', 
            'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC',
            'EXECUTE', 'MERGE', 'CALL', 'REPLACE', 'RENAME',
            'BACKUP', 'RESTORE', 'ATTACH', 'DETACH'
        ]
        
        query_upper = v.upper()
        for keyword in dangerous_keywords:
            # Check for keyword as a whole word to avoid false positives
            if re.search(r'\b' + keyword + r'\b', query_upper):
                raise ValueError(f"Dangerous SQL operation '{keyword}' not allowed. Only read operations are permitted.")
        
        # Security: Block SQL injection patterns
        injection_patterns = [
            r';[^;]*$',  # Multiple statements
            r'--',       # SQL comments
            r'/\*',      # Block comments start
            r'\*/',      # Block comments end
            r'@@',       # Global variables
            r'xp_',      # Extended procedures
            r'sp_',      # Stored procedures
            r'0x[0-9a-fA-F]+',  # Hex literals that could be used for injection
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, v):
                raise ValueError("Potentially malicious SQL pattern detected")
        
        # Only allow safe read operations
        safe_keywords = ['SELECT', 'DESCRIBE', 'SHOW', 'WITH', 'EXPLAIN', 'PRAGMA']
        if not any(re.search(r'\b' + keyword + r'\b', query_upper) for keyword in safe_keywords):
            raise ValueError("Only read operations (SELECT, DESCRIBE, SHOW, WITH) are allowed")
            
        return v


class QueryResult(BaseModel):
    """Result from database query execution."""
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int


class AnalystResponse(BaseModel):
    """Structured response from the AI analyst."""
    text_answer: str
    sql_query: str
    status: QueryStatus
    error_message: Optional[str] = None
    raw_data: Optional[List[Dict[str, Any]]] = None


class ConversationContext(BaseModel):
    """Context information for maintaining conversation state."""
    question: str
    previous_sql: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    aggregations: List[str] = Field(default_factory=list)
    tables: List[str] = Field(default_factory=list)


class ConversationState:
    """State management for conversation sessions."""
    def __init__(self):
        self.messages: List[Dict[str, str]] = []
        self.current_question: str = ""
        self.sql_history: List[str] = []
        self.context_stack: List[ConversationContext] = []
        self.last_context: Optional[ConversationContext] = None
        self.retry_count: int = 0
