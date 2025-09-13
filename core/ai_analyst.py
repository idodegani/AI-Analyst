"""
AI Analyst integration for Django chat application
Based on ai_analyst_v3.py logic
"""

import os
import pandas as pd
import duckdb
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import asyncio
import json
import re
from enum import Enum

# Pydantic for data validation
from pydantic import BaseModel, Field, field_validator

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# OpenAI
from openai import OpenAI

# Django imports
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Pydantic Models
class QueryStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    RETRY = "retry"

class SQLQuery(BaseModel):
    """Validated SQL Query"""
    query: str
    is_valid: bool = True
    error_message: Optional[str] = None
    
    @field_validator('query')
    def validate_sql(cls, v):
        # Clean up the query
        v = v.strip()
        
        # Remove markdown formatting
        v = re.sub(r'^```(?:sql)?', '', v)
        v = re.sub(r'```$', '', v)
        v = v.strip()
        
        # Check if it's actually SQL
        sql_keywords = ['SELECT', 'DESCRIBE', 'SHOW', 'WITH']
        if not any(keyword in v.upper() for keyword in sql_keywords):
            raise ValueError("Not a valid SQL query")
            
        return v

class QueryResult(BaseModel):
    """Result from database query"""
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    
class AnalystResponse(BaseModel):
    """Structured response from the analyst"""
    text_answer: str
    sql_query: str
    status: QueryStatus
    error_message: Optional[str] = None
    raw_data: Optional[List[Dict[str, Any]]] = None

class ConversationContext(BaseModel):
    """Context information for conversation"""
    question: str
    previous_sql: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    aggregations: List[str] = Field(default_factory=list)
    tables: List[str] = Field(default_factory=list)

class ConversationState:
    """Enhanced state management with structured data"""
    def __init__(self):
        self.messages: List[Dict[str, str]] = []
        self.current_question: str = ""
        self.sql_history: List[str] = []
        self.context_stack: List[ConversationContext] = []
        self.last_context: Optional[ConversationContext] = None
        self.retry_count: int = 0

class AIAnalystDjango:
    """AI-powered data analyst integrated with Django"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIAnalystDjango, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            logger.info("🚀 Initializing AI Agent Analyst for Django...")
            self.conn = duckdb.connect(':memory:')
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.show_sql = True
            self.max_retries = 1
            self.sessions_state = {}  # Store state per session
            self.load_data()
            self.setup_workflow()
            self._initialized = True
            logger.info("✅ AI Analyst ready!")
    
    def get_session_state(self, session_id: str) -> ConversationState:
        """Get or create state for a session"""
        if session_id not in self.sessions_state:
            self.sessions_state[session_id] = ConversationState()
        return self.sessions_state[session_id]
        
    def load_data(self):
        """Load CSV data into DuckDB"""
        try:
            # Load reservations with proper date parsing
            reservations_df = pd.read_csv("reservations.csv")
            
            # Convert date columns to datetime
            date_columns = ['created_at', 'check_in', 'check_out']
            for col in date_columns:
                if col in reservations_df.columns:
                    reservations_df[col] = pd.to_datetime(reservations_df[col], errors='coerce')
            
            self.conn.execute("CREATE TABLE reservations AS SELECT * FROM reservations_df")
            
            # Load reviews
            reviews_df = pd.read_csv("reviews.csv")
            self.conn.execute("CREATE TABLE reviews AS SELECT * FROM reviews_df")
            
            logger.info(f"📊 Loaded {len(reservations_df):,} reservations and {len(reviews_df):,} reviews")
            
            # Store schema information for reference
            self.schema_info = self._get_schema_info()
            
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
            raise
    
    def _get_schema_info(self) -> str:
        """Get formatted schema information"""
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
            
    def setup_workflow(self):
        """Setup LangGraph workflow"""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("generate_sql", self.generate_sql)
        workflow.add_node("execute_query", self.execute_query)
        workflow.add_node("format_response", self.format_response)
        workflow.add_node("handle_error", self.handle_error)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "generate_sql",
            lambda x: "execute_query" if x.get("sql_valid", False) else "handle_error"
        )
        
        workflow.add_conditional_edges(
            "execute_query",
            lambda x: "format_response" if x.get("success", False) else "handle_error"
        )
        
        workflow.add_conditional_edges(
            "handle_error",
            lambda x: "generate_sql" if x.get("retry", False) and x.get("retry_count", 0) < self.max_retries else "format_response"
        )
        
        workflow.add_edge("format_response", END)
        
        # Set entry point
        workflow.set_entry_point("generate_sql")
        
        # Compile
        self.app = workflow.compile()
    
    def extract_context(self, question: str, sql: str) -> ConversationContext:
        """Extract context from question and SQL"""
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
        
    def generate_sql(self, state: dict) -> dict:
        """Generate SQL query with better prompting and validation"""
        
        session_id = state.get("session_id")
        session_state = self.get_session_state(session_id)
        question = session_state.current_question
        
        # Enhanced system prompt with examples
        system_prompt = """You are a SQL expert for DuckDB. Generate SQL queries for these tables:

TABLES:
- reservations: reservation_id (BIGINT), account_id (BIGINT), listing_id (BIGINT), status (VARCHAR), created_at (TIMESTAMP), check_in (TIMESTAMP), check_out (TIMESTAMP), fee_host_payout_usd (DOUBLE), guest_count (DOUBLE), nights_count (DOUBLE), booking_window (BIGINT)
- reviews: review_id (VARCHAR), reservation_id (BIGINT), overall_rating (DOUBLE), cleaniness_rating (DOUBLE), location_rating (DOUBLE)

CRITICAL RULES:
1. ONLY return the SQL query - no explanations, no markdown, no comments
2. The column is spelled 'cleaniness_rating' (with typo), NOT 'cleanliness_rating'
3. review_id is VARCHAR - use quotes: WHERE review_id = '1234'
4. For date filtering use EXTRACT: EXTRACT(MONTH FROM created_at) = 3 AND EXTRACT(YEAR FROM created_at) = 2025
5. For Q1/Q2/Q3/Q4, use IN clause: EXTRACT(MONTH FROM created_at) IN (1,2,3) for Q1
6. For H1/H2 (half year), use IN clause: EXTRACT(MONTH FROM created_at) IN (1,2,3,4,5,6) for H1

EXAMPLES:
- "average guest count for Q1 2025" → SELECT AVG(guest_count) FROM reservations WHERE EXTRACT(MONTH FROM created_at) IN (1,2,3) AND EXTRACT(YEAR FROM created_at) = 2025
- "average guest count for H1 2025" → SELECT AVG(guest_count) FROM reservations WHERE EXTRACT(MONTH FROM created_at) IN (1,2,3,4,5,6) AND EXTRACT(YEAR FROM created_at) = 2025

IMPORTANT: Return ONLY the SQL query, nothing else."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context for follow-up questions
        if session_state.last_context and self._is_follow_up(question):
            context_msg = f"Previous query context: {session_state.last_context.previous_sql}"
            messages.append({"role": "system", "content": context_msg})
        
        # Add conversation history for context
        for msg in session_state.messages[-4:]:  # Last 4 messages
            if msg.get("role") == "user":
                messages.append({"role": "user", "content": f"Previous question: {msg['content']}"})
        
        messages.append({"role": "user", "content": f"Generate SQL for: {question}"})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0
            )
            
            sql_text = response.choices[0].message.content.strip()
            
            # Validate SQL using Pydantic
            try:
                sql_query = SQLQuery(query=sql_text)
                state["sql_query"] = sql_query.query
                state["sql_valid"] = True
            except ValueError as e:
                state["sql_query"] = sql_text
                state["sql_valid"] = False
                state["error"] = f"Invalid SQL generated: {str(e)}"
                
        except Exception as e:
            state["error"] = f"Failed to generate SQL: {str(e)}"
            state["sql_valid"] = False
            
        return state
    
    def _is_follow_up(self, question: str) -> bool:
        """Check if question is a follow-up"""
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
        
    def execute_query(self, state: dict) -> dict:
        """Execute SQL query with better error handling"""
        session_id = state.get("session_id")
        session_state = self.get_session_state(session_id)
        
        try:
            sql_query = state.get("sql_query", "")
            
            result = self.conn.execute(sql_query).fetchall()
            columns = [desc[0] for desc in self.conn.description]
            
            # Convert to list of dicts
            data = []
            for row in result:
                data.append(dict(zip(columns, row)))
            
            # Create QueryResult
            query_result = QueryResult(
                data=data,
                columns=columns,
                row_count=len(data)
            )
            
            state["query_result"] = query_result.model_dump()
            state["success"] = True
            
            # Store context
            context = self.extract_context(session_state.current_question, sql_query)
            session_state.last_context = context
            session_state.sql_history.append(sql_query)
            
        except Exception as e:
            error_msg = str(e)
            state["error"] = self._enhance_error_message(error_msg)
            state["success"] = False
            
        return state
    
    def _enhance_error_message(self, error_msg: str) -> str:
        """Enhance error messages with helpful hints"""
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
    
    def handle_error(self, state: dict) -> dict:
        """Handle errors and decide whether to retry"""
        retry_count = state.get("retry_count", 0)
        
        if retry_count < self.max_retries:
            state["retry"] = True
            state["retry_count"] = retry_count + 1
            
            # Add error context for retry
            error_msg = state.get("error", "Unknown error")
            state["error_context"] = f"Previous attempt failed with: {error_msg}. Please fix the issue."
        else:
            state["retry"] = False
            
        return state
        
    def format_response(self, state: dict) -> dict:
        """Format response with GPT-generated natural language answer"""
        
        session_id = state.get("session_id")
        session_state = self.get_session_state(session_id)
        
        # Check if we have an error
        if not state.get("success", False):
            error_msg = state.get("error", "Unknown error occurred")
            state["response"] = AnalystResponse(
                text_answer=f"I encountered an error: {error_msg}",
                sql_query=state.get("sql_query", ""),
                status=QueryStatus.ERROR,
                error_message=error_msg
            )
            return state
        
        try:
            query_result = state.get("query_result", {})
            data = query_result.get("data", [])
            sql_query = state.get("sql_query", "")
            
            # Generate natural language response using GPT
            system_prompt = """You are a data analyst assistant. Given a user's question, the SQL query executed, and the results, 
provide a clear, natural language answer. Be concise but informative. Format numbers nicely (e.g., 2.67 for averages, 
$474.66 for currency). If the result is a single value, state it clearly. If multiple results, summarize appropriately."""
            
            user_prompt = f"""Question: {session_state.current_question}
SQL Query: {sql_query}
Results: {json.dumps(data, default=str)}

Provide a natural language answer to the question based on these results."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.3
            )
            
            text_answer = response.choices[0].message.content.strip()
            
            # Create structured response
            state["response"] = AnalystResponse(
                text_answer=text_answer,
                sql_query=sql_query,
                status=QueryStatus.SUCCESS,
                raw_data=data if len(data) <= 10 else data[:10]  # Limit raw data
            )
            
        except Exception as e:
            state["response"] = AnalystResponse(
                text_answer=f"Error formatting response: {str(e)}",
                sql_query=state.get("sql_query", ""),
                status=QueryStatus.ERROR,
                error_message=str(e)
            )
            
        return state
        
    async def ask(self, question: str, session_id: str) -> AnalystResponse:
        """Process a question and return structured response"""
        session_state = self.get_session_state(session_id)
        session_state.current_question = question
        session_state.retry_count = 0
        session_state.messages.append({"role": "user", "content": question})
        
        # Run workflow
        result = await self.app.ainvoke({"question": question, "session_id": session_id})
        
        # Get response
        response = result.get("response")
        if isinstance(response, AnalystResponse):
            session_state.messages.append({"role": "assistant", "content": response.text_answer})
            return response
        else:
            # Fallback
            return AnalystResponse(
                text_answer="I couldn't process your question.",
                sql_query="",
                status=QueryStatus.ERROR,
                error_message="Unexpected response format"
            )

# Singleton instance
_analyst_instance = None

def get_analyst():
    """Get the singleton AI analyst instance"""
    global _analyst_instance
    if _analyst_instance is None:
        _analyst_instance = AIAnalystDjango()
    return _analyst_instance
