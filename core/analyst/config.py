"""
Configuration management for the AI Analyst system.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    connection_string: str = ':memory:'
    reservations_file: str = "reservations.csv"
    reviews_file: str = "reviews.csv"
    date_columns: List[str] = None
    
    def __post_init__(self):
        if self.date_columns is None:
            self.date_columns = ['created_at', 'check_in', 'check_out']


@dataclass
class LLMConfig:
    """Language model configuration settings."""
    model_name: str = "gpt-4"
    sql_generation_model: str = "gpt-4.1-mini"
    temperature: float = 0.3
    sql_temperature: float = 0.0
    max_context_messages: int = 4


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    max_retries: int = 1
    allowed_sql_operations: List[str] = None
    dangerous_sql_keywords: List[str] = None
    injection_patterns: List[str] = None
    
    def __post_init__(self):
        if self.allowed_sql_operations is None:
            self.allowed_sql_operations = ['SELECT', 'WITH', 'DESCRIBE', 'SHOW', 'EXPLAIN', 'PRAGMA']
        
        if self.dangerous_sql_keywords is None:
            self.dangerous_sql_keywords = [
                'DELETE', 'DROP', 'TRUNCATE', 'INSERT', 'UPDATE',
                'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC',
                'EXECUTE', 'MERGE', 'CALL', 'REPLACE', 'RENAME',
                'BACKUP', 'RESTORE', 'ATTACH', 'DETACH'
            ]
        
        if self.injection_patterns is None:
            self.injection_patterns = [
                r';[^;]*$',  # Multiple statements
                r'--',       # SQL comments
                r'/\*',      # Block comments start
                r'\*/',      # Block comments end
                r'@@',       # Global variables
                r'xp_',      # Extended procedures
                r'sp_',      # Stored procedures
                r'0x[0-9a-fA-F]+',  # Hex literals
            ]


@dataclass
class AnalystConfig:
    """Main configuration for the AI Analyst system."""
    database: DatabaseConfig = None
    llm: LLMConfig = None
    security: SecurityConfig = None
    show_sql: bool = True
    max_raw_data_items: int = 10
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.security is None:
            self.security = SecurityConfig()


# Default configuration instance
default_config = AnalystConfig()
