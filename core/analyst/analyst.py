"""
Main AI Analyst implementation with modular architecture.
"""

import logging
from typing import Dict, Optional

from .models import ConversationState, AnalystResponse, QueryStatus
from .config import AnalystConfig, default_config
from .providers import DuckDBProvider, OpenAIProvider
from .services import QueryService, ResponseService
from .validators import SQLSecurityValidator
from .workflow import AnalystWorkflow

logger = logging.getLogger(__name__)


class AIAnalystDjango:
    """AI-powered data analyst with modular architecture."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIAnalystDjango, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[AnalystConfig] = None):
        if not self._initialized:
            logger.info("🚀 Initializing AI Agent Analyst for Django...")
            
            # Use provided config or default
            self.config = config or default_config
            
            # Initialize providers
            self.db_provider = DuckDBProvider(self.config.database)
            self.llm_provider = OpenAIProvider(self.config.llm)
            
            # Initialize validator
            self.validator = SQLSecurityValidator(self.config.security)
            
            # Initialize services
            self.query_service = QueryService(
                db_provider=self.db_provider,
                llm_provider=self.llm_provider,
                validator=self.validator,
                config=self.config
            )
            
            self.response_service = ResponseService(
                llm_provider=self.llm_provider,
                config=self.config
            )
            
            # Initialize workflow
            self.workflow = AnalystWorkflow(
                query_service=self.query_service,
                response_service=self.response_service,
                validator=self.validator,
                max_retries=self.config.security.max_retries
            )
            
            # Session management
            self.sessions_state: Dict[str, ConversationState] = {}
            
            # Store schema info
            self.schema_info = self.db_provider.get_schema_info()
            
            # Configuration flags
            self.show_sql = self.config.show_sql
            self.max_retries = self.config.security.max_retries
            
            self._initialized = True
            logger.info("✅ AI Analyst ready!")
    
    def get_session_state(self, session_id: str) -> ConversationState:
        """Get or create state for a session."""
        if session_id not in self.sessions_state:
            self.sessions_state[session_id] = ConversationState()
        return self.sessions_state[session_id]
    
    async def ask(self, question: str, session_id: str) -> AnalystResponse:
        """
        Process a question and return structured response.
        
        This method maintains the exact same interface as the original implementation
        to ensure compatibility with existing code.
        """
        session_state = self.get_session_state(session_id)
        session_state.current_question = question
        session_state.retry_count = 0
        session_state.messages.append({"role": "user", "content": question})
        
        try:
            # Run workflow
            response = await self.workflow.run(session_state, self.schema_info)
            
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
                
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return AnalystResponse(
                text_answer=f"An error occurred: {str(e)}",
                sql_query="",
                status=QueryStatus.ERROR,
                error_message=str(e)
            )


# Singleton instance
_analyst_instance = None


def get_analyst() -> AIAnalystDjango:
    """
    Get the singleton AI analyst instance.
    
    This function maintains the exact same interface as the original implementation
    to ensure compatibility with existing code.
    """
    global _analyst_instance
    if _analyst_instance is None:
        _analyst_instance = AIAnalystDjango()
    return _analyst_instance
