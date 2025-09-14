"""
Prompt builders for the AI Analyst system.
"""

from typing import List, Dict
from .models import ConversationState


class SQLPromptBuilder:
    """Builds prompts for SQL generation."""
    
    @staticmethod
    def build_system_prompt() -> str:
        """Build the system prompt for SQL generation."""
        return """You are a SQL expert for DuckDB. Generate SQL queries for these tables:

TABLES:
- reservations: reservation_id (BIGINT), account_id (BIGINT), listing_id (BIGINT), status (VARCHAR), created_at (TIMESTAMP), check_in (TIMESTAMP), check_out (TIMESTAMP), fee_host_payout_usd (DOUBLE), guest_count (DOUBLE), nights_count (DOUBLE), booking_window (BIGINT)
- reviews: review_id (VARCHAR), reservation_id (BIGINT), overall_rating (DOUBLE), cleaniness_rating (DOUBLE), location_rating (DOUBLE)

🔒 SECURITY RULES (CRITICAL):
- ONLY generate SELECT, DESCRIBE, SHOW, WITH, or EXPLAIN queries
- NEVER generate DELETE, DROP, UPDATE, INSERT, ALTER, CREATE, TRUNCATE, or any data modification queries
- NEVER include multiple statements separated by semicolons
- NEVER include SQL comments (-- or /* */)
- If asked to modify/delete/update data, respond with: SELECT 'I can only read data, not modify it' as error_message

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
- "delete all reservations" → SELECT 'I can only read data, not modify it' as error_message

IMPORTANT: Return ONLY the SQL query, nothing else."""
    
    @staticmethod
    def build_messages(session_state: ConversationState, schema_info: str, 
                      is_follow_up: bool, max_context_messages: int) -> List[Dict[str, str]]:
        """Build messages for SQL generation."""
        messages = [{"role": "system", "content": SQLPromptBuilder.build_system_prompt()}]
        
        # Add context for follow-up questions
        if session_state.last_context and is_follow_up:
            context_msg = f"Previous query context: {session_state.last_context.previous_sql}"
            messages.append({"role": "system", "content": context_msg})
        
        # Add conversation history for context
        for msg in session_state.messages[-max_context_messages:]:
            if msg.get("role") == "user":
                messages.append({"role": "user", "content": f"Previous question: {msg['content']}"})
        
        messages.append({"role": "user", "content": f"Generate SQL for: {session_state.current_question}"})
        
        return messages


class ResponsePromptBuilder:
    """Builds prompts for natural language response generation."""
    
    @staticmethod
    def build_system_prompt() -> str:
        """Build the system prompt for response generation."""
        return """You are a data analyst assistant. Given a user's question, the SQL query executed, and the results, 
provide a clear, natural language answer. Be concise but informative. Format numbers nicely (e.g., 2.67 for averages, 
$474.66 for currency). If the result is a single value, state it clearly. If multiple results, summarize appropriately."""
    
    @staticmethod
    def build_messages(question: str, sql_query: str, results: str) -> List[Dict[str, str]]:
        """Build messages for response generation."""
        user_prompt = f"""Question: {question}
SQL Query: {sql_query}
Results: {results}

Provide a natural language answer to the question based on these results."""
        
        return [
            {"role": "system", "content": ResponsePromptBuilder.build_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]
