"""
External service providers for the AI Analyst system.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
import duckdb
from openai import OpenAI
from django.conf import settings
import logging

from .models import QueryResult
from .config import DatabaseConfig, LLMConfig

logger = logging.getLogger(__name__)


class DatabaseProvider(ABC):
    """Abstract base class for database providers."""
    
    @abstractmethod
    def execute_query(self, query: str) -> QueryResult:
        """Execute a SQL query and return results."""
        pass
    
    @abstractmethod
    def get_schema_info(self) -> str:
        """Get formatted schema information."""
        pass


class DuckDBProvider(DatabaseProvider):
    """DuckDB implementation of database provider."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.conn = duckdb.connect(config.connection_string)
        self._load_data()
    
    def _load_data(self):
        """Load CSV data into DuckDB."""
        try:
            # Load reservations with proper date parsing
            reservations_df = pd.read_csv(self.config.reservations_file)
            
            # Convert date columns to datetime
            for col in self.config.date_columns:
                if col in reservations_df.columns:
                    reservations_df[col] = pd.to_datetime(reservations_df[col], errors='coerce')
            
            self.conn.execute("CREATE TABLE reservations AS SELECT * FROM reservations_df")
            
            # Load reviews
            reviews_df = pd.read_csv(self.config.reviews_file)
            self.conn.execute("CREATE TABLE reviews AS SELECT * FROM reviews_df")
            
            logger.info(f"📊 Loaded {len(reservations_df):,} reservations and {len(reviews_df):,} reviews")
            
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
            raise
    
    def execute_query(self, query: str) -> QueryResult:
        """Execute SQL query and return results."""
        result = self.conn.execute(query).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        
        # Convert to list of dicts
        data = []
        for row in result:
            data.append(dict(zip(columns, row)))
        
        return QueryResult(
            data=data,
            columns=columns,
            row_count=len(data)
        )
    
    def get_schema_info(self) -> str:
        """Get formatted schema information."""
        schema_text = ""
        
        # Reservations schema
        schema_text += "RESERVATIONS table:\n"
        res_schema = self.conn.execute("DESCRIBE reservations").fetchall()
        for col_info in res_schema[:5]:
            schema_text += f"  - {col_info[0]}: {col_info[1]}\n"
        if len(res_schema) > 5:
            schema_text += f"  ... and {len(res_schema) - 5} more columns\n"
        
        schema_text += "\nREVIEWS table:\n"
        rev_schema = self.conn.execute("DESCRIBE reviews").fetchall()
        for col_info in rev_schema:
            schema_text += f"  - {col_info[0]}: {col_info[1]}\n"
            
        return schema_text


class LLMProvider(ABC):
    """Abstract base class for language model providers."""
    
    @abstractmethod
    def generate_sql(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """Generate SQL query from messages."""
        pass
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """Generate natural language response."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate_sql(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """Generate SQL query using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.config.sql_generation_model,
            messages=messages,
            temperature=temperature or self.config.sql_temperature
        )
        return response.choices[0].message.content.strip()
    
    def generate_response(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """Generate natural language response using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=temperature or self.config.temperature
        )
        return response.choices[0].message.content.strip()
