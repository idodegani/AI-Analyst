"""
Workflow orchestration for the AI Analyst system.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
import logging

from .models import ConversationState, QueryStatus
from .services import QueryService, ResponseService, ContextExtractor
from .validators import SQLSecurityValidator

logger = logging.getLogger(__name__)


class AnalystWorkflow:
    """Orchestrates the AI analyst workflow using LangGraph."""
    
    def __init__(self, query_service: QueryService, response_service: ResponseService,
                 validator: SQLSecurityValidator, max_retries: int = 1):
        self.query_service = query_service
        self.response_service = response_service
        self.validator = validator
        self.max_retries = max_retries
        self.app = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("generate_sql", self._generate_sql_node)
        workflow.add_node("validate_security", self._validate_security_node)
        workflow.add_node("execute_query", self._execute_query_node)
        workflow.add_node("format_response", self._format_response_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "generate_sql",
            lambda x: "validate_security" if x.get("sql_valid", False) else "handle_error"
        )
        
        workflow.add_conditional_edges(
            "validate_security",
            lambda x: "execute_query" if x.get("security_passed", False) else "handle_error"
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
        return workflow.compile()
    
    def _generate_sql_node(self, state: dict) -> dict:
        """Generate SQL query node."""
        session_state = state.get("session_state")
        schema_info = state.get("schema_info")
        
        sql_query, is_valid, error = self.query_service.generate_sql(session_state, schema_info)
        
        state["sql_query"] = sql_query
        state["sql_valid"] = is_valid
        if error:
            state["error"] = error
            
        return state
    
    def _validate_security_node(self, state: dict) -> dict:
        """Security validation node."""
        sql_query = state.get("sql_query", "")
        
        is_valid, error = self.validator.validate_query(sql_query)
        
        state["security_passed"] = is_valid
        if error:
            state["error"] = error
        else:
            logger.info(f"✅ Security validation passed for query: {sql_query[:50]}...")
            
        return state
    
    def _execute_query_node(self, state: dict) -> dict:
        """Execute query node."""
        sql_query = state.get("sql_query", "")
        session_state = state.get("session_state")
        
        query_result, success, error = self.query_service.execute_query(sql_query)
        
        state["query_result"] = query_result
        state["success"] = success
        if error:
            state["error"] = error
        
        # Store context on success
        if success and session_state:
            context = ContextExtractor.extract_context(session_state.current_question, sql_query)
            session_state.last_context = context
            session_state.sql_history.append(sql_query)
            
        return state
    
    def _format_response_node(self, state: dict) -> dict:
        """Format response node."""
        session_state = state.get("session_state")
        
        response = self.response_service.format_response(
            question=session_state.current_question,
            sql_query=state.get("sql_query", ""),
            query_result=state.get("query_result", {}),
            success=state.get("success", False),
            error_msg=state.get("error", "")
        )
        
        state["response"] = response
        return state
    
    def _handle_error_node(self, state: dict) -> dict:
        """Handle error and retry logic."""
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
    
    async def run(self, session_state: ConversationState, schema_info: str) -> Any:
        """Run the workflow asynchronously."""
        initial_state = {
            "session_state": session_state,
            "schema_info": schema_info
        }
        
        result = await self.app.ainvoke(initial_state)
        return result.get("response")
