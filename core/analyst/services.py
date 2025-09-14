"""
Business logic services for the AI Analyst system.
"""

import re
import json
from typing import List, Dict, Any, Optional
import logging

from .models import ConversationContext, ConversationState, AnalystResponse, QueryStatus, SQLQuery
from .providers import DatabaseProvider, LLMProvider
from .validators import SQLSecurityValidator
from .config import AnalystConfig
from .prompts import SQLPromptBuilder, ResponsePromptBuilder

logger = logging.getLogger(__name__)


class ContextExtractor:
    """Extracts and manages conversation context."""
    
    @staticmethod
    def extract_context(question: str, sql: str) -> ConversationContext:
        """Extract context from question and SQL."""
        context = ConversationContext(question=question, previous_sql=sql)
        
        # Extract date filters
        # Handle Q1, Q2, Q3, Q4 (quarters)
        quarter_mapping = {
            'q1': [1, 2, 3],
            'q2': [4, 5, 6],
            'q3': [7, 8, 9],
            'q4': [10, 11, 12]
        }
        
        # Handle H1, H2 (half years)
        half_mapping = {
            'h1': [1, 2, 3, 4, 5, 6],
            'h2': [7, 8, 9, 10, 11, 12]
        }
        
        question_lower = question.lower()
        
        # Check for quarters
        for quarter, months in quarter_mapping.items():
            if quarter in question_lower:
                context.filters['quarter'] = quarter
                context.filters['months'] = months
                
        # Check for half years
        for half, months in half_mapping.items():
            if half in question_lower:
                context.filters['half'] = half
                context.filters['months'] = months
        
        # Extract month/year from SQL
        month_match = re.search(r'EXTRACT\(MONTH FROM (\w+)\) = (\d+)', sql)
        year_match = re.search(r'EXTRACT\(YEAR FROM (\w+)\) = (\d+)', sql)
        
        if month_match:
            context.filters["month"] = int(month_match.group(2))
            context.filters["month_column"] = month_match.group(1)
        if year_match:
            context.filters["year"] = int(year_match.group(2))
            context.filters["year_column"] = year_match.group(1)
            
        # Extract tables
        if "reservations" in sql.lower():
            context.tables.append("reservations")
        if "reviews" in sql.lower():
            context.tables.append("reviews")
            
        # Extract aggregations
        for agg in ["AVG", "SUM", "COUNT", "MAX", "MIN"]:
            if agg in sql.upper():
                context.aggregations.append(agg)
                
        return context
    
    @staticmethod
    def is_follow_up(question: str) -> bool:
        """Check if question is a follow-up."""
        follow_up_patterns = [
            r'\band\s+(for|what|how)',
            r'^(and|but|also|what about|how about)',
            r'(them|those|these|that|it)(?:\s|$)',
            r'(instead|rather than|compared to)',
        ]
        
        question_lower = question.lower()
        for pattern in follow_up_patterns:
            if re.search(pattern, question_lower):
                return True
        return False


class ErrorEnhancer:
    """Enhances error messages with helpful hints."""
    
    @staticmethod
    def enhance_error_message(error_msg: str) -> str:
        """Enhance error messages with helpful hints."""
        if "Parser Error" in error_msg:
            return "SQL syntax error. The query may contain invalid syntax."
        elif "Referenced column" in error_msg and "cleanliness" in error_msg:
            return f"{error_msg}\n💡 Hint: The column is spelled 'cleaniness_rating' (with typo)"
        elif "Could not convert string" in error_msg and "review_id" in error_msg:
            return f"{error_msg}\n💡 Hint: review_id is VARCHAR - use quotes: WHERE review_id = '1234'"
        elif "date_part" in error_msg or "extract" in error_msg:
            return f"{error_msg}\n💡 Hint: Use: EXTRACT(MONTH FROM created_at) = 3"
        else:
            return f"Query execution failed: {error_msg}"


class QueryService:
    """Service for handling SQL query generation and execution."""
    
    def __init__(self, db_provider: DatabaseProvider, llm_provider: LLMProvider, 
                 validator: SQLSecurityValidator, config: AnalystConfig):
        self.db_provider = db_provider
        self.llm_provider = llm_provider
        self.validator = validator
        self.config = config
        self.prompt_builder = SQLPromptBuilder()
        self.error_enhancer = ErrorEnhancer()
    
    def generate_sql(self, session_state: ConversationState, schema_info: str) -> tuple[str, bool, str]:
        """
        Generate SQL query for the current question.
        
        Returns:
            Tuple of (sql_query, is_valid, error_message)
        """
        try:
            messages = self.prompt_builder.build_messages(
                session_state=session_state,
                schema_info=schema_info,
                is_follow_up=ContextExtractor.is_follow_up(session_state.current_question),
                max_context_messages=self.config.llm.max_context_messages
            )
            
            sql_text = self.llm_provider.generate_sql(messages)
            
            # Validate SQL using Pydantic
            sql_query = SQLQuery(query=sql_text)
            return sql_query.query, True, ""
            
        except ValueError as e:
            return sql_text, False, f"Invalid SQL generated: {str(e)}"
        except Exception as e:
            return "", False, f"Failed to generate SQL: {str(e)}"
    
    def execute_query(self, sql_query: str) -> tuple[Optional[Dict[str, Any]], bool, str]:
        """
        Execute SQL query with security validation.
        
        Returns:
            Tuple of (query_result, success, error_message)
        """
        # Final security check
        is_valid, error = self.validator.validate_query(sql_query)
        if not is_valid:
            return None, False, error
        
        try:
            query_result = self.db_provider.execute_query(sql_query)
            return query_result.model_dump(), True, ""
        except Exception as e:
            error_msg = self.error_enhancer.enhance_error_message(str(e))
            return None, False, error_msg


class ResponseService:
    """Service for generating natural language responses."""
    
    def __init__(self, llm_provider: LLMProvider, config: AnalystConfig):
        self.llm_provider = llm_provider
        self.config = config
        self.prompt_builder = ResponsePromptBuilder()
    
    def format_response(self, question: str, sql_query: str, 
                       query_result: Dict[str, Any], success: bool, 
                       error_msg: str = "") -> AnalystResponse:
        """Format the final response for the user."""
        if not success:
            return AnalystResponse(
                text_answer=f"I encountered an error: {error_msg}",
                sql_query=sql_query,
                status=QueryStatus.ERROR,
                error_message=error_msg
            )
        
        try:
            data = query_result.get("data", [])
            
            messages = self.prompt_builder.build_messages(
                question=question,
                sql_query=sql_query,
                results=json.dumps(data, default=str)
            )
            
            text_answer = self.llm_provider.generate_response(messages)
            
            return AnalystResponse(
                text_answer=text_answer,
                sql_query=sql_query,
                status=QueryStatus.SUCCESS,
                raw_data=data if len(data) <= self.config.max_raw_data_items else data[:self.config.max_raw_data_items]
            )
            
        except Exception as e:
            return AnalystResponse(
                text_answer=f"Error formatting response: {str(e)}",
                sql_query=sql_query,
                status=QueryStatus.ERROR,
                error_message=str(e)
            )
