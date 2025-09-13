import os
import json
import asyncio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import ChatSession, ChatMessage
from .ai_analyst import get_analyst, QueryStatus
import logging

logger = logging.getLogger(__name__)

# Configuration - these should be in environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "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")

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


@csrf_exempt
@require_http_methods(["GET"])
def get_sessions(request):
    """Get all chat sessions"""
    try:
        sessions = ChatSession.objects.all()
        sessions_data = []
        
        for session in sessions:
            sessions_data.append({
                'id': session.session_id,  # Use session_id as id for frontend compatibility
                'session_id': session.session_id,
                'guesty_session_id': session.guesty_session_id,
                'title': session.title,
                'message_count': session.message_count,
                'last_message': session.last_message,
                'created_date': session.created_at.isoformat()
            })
        
        return JsonResponse({'sessions': sessions_data})
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    """Create a new chat session"""
    try:
        data = json.loads(request.body)
        
        session = ChatSession.objects.create(
            session_id=data['session_id'],
            guesty_session_id=data['guesty_session_id'],
            title=data.get('title', 'New Chat'),
            message_count=data.get('message_count', 0),
            last_message=data.get('last_message', '')
        )
        
        return JsonResponse({
            'id': data['session_id'],  # Return session_id as id for frontend compatibility
            'session_id': session.session_id,
            'guesty_session_id': session.guesty_session_id,
            'title': session.title,
            'message_count': session.message_count,
            'last_message': session.last_message,
            'created_date': session.created_at.isoformat()
        })
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    """Delete a chat session"""
    try:
        session = ChatSession.objects.get(session_id=session_id)
        session.delete()
        return JsonResponse({'success': True})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_messages(request, session_id):
    """Get all messages for a session"""
    try:
        session = ChatSession.objects.get(session_id=session_id)
        messages = session.messages.all()
        
        messages_data = []
        for message in messages:
            msg_data = {
                'id': str(message.id),  # Convert UUID to string for frontend
                'session_id': session_id,
                'content': message.content,
                'role': message.role,
                'timestamp': message.timestamp.isoformat()
            }
            # Include SQL query for assistant messages
            if message.role == 'assistant' and message.sql_query:
                msg_data['sql_query'] = message.sql_query
                msg_data['query_status'] = message.query_status
            
            messages_data.append(msg_data)
        
        return JsonResponse({'messages': messages_data})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Send a message and get AI response using AI Analyst"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        content = data.get('content')
        
        if not session_id or not content:
            return JsonResponse({'error': 'session_id and content are required'}, status=400)
        
        # Get or create session
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            content=content,
            role='user'
        )
        
        # Get AI analyst instance
        analyst = get_analyst()
        
        # Process the question using AI analyst
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(analyst.ask(content, session_id))
        finally:
            loop.close()
        
        # Save AI response with SQL query
        ai_message = ChatMessage.objects.create(
            session=session,
            content=response.text_answer,
            role='assistant',
            sql_query=response.sql_query,
            query_status=response.status.value
        )
        
        # Update session metadata
        session.message_count = session.messages.count()
        session.last_message = content[:100]
        if session.message_count == 2:  # First exchange
            session.title = content[:50]
        session.save()
        
        # Return both messages with SQL query
        return JsonResponse({
            'user_message': {
                'id': str(user_message.id),  # Convert UUID to string
                'session_id': session_id,
                'content': user_message.content,
                'role': user_message.role,
                'timestamp': user_message.timestamp.isoformat()
            },
            'ai_message': {
                'id': str(ai_message.id),  # Convert UUID to string
                'session_id': session_id,
                'content': ai_message.content,
                'role': ai_message.role,
                'timestamp': ai_message.timestamp.isoformat(),
                'sql_query': ai_message.sql_query,
                'query_status': ai_message.query_status
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
def update_session(request, session_id):
    """Update session metadata"""
    try:
        data = json.loads(request.body)
        session = ChatSession.objects.get(session_id=session_id)
        
        if 'title' in data:
            session.title = data['title']
        if 'guesty_session_id' in data:
            session.guesty_session_id = data['guesty_session_id']
        
        session.save()
        
        return JsonResponse({
            'id': session.session_id,  # Use session_id as id for frontend compatibility
            'session_id': session.session_id,
            'guesty_session_id': session.guesty_session_id,
            'title': session.title,
            'message_count': session.message_count,
            'last_message': session.last_message,
            'created_date': session.created_at.isoformat()
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        return JsonResponse({'error': str(e)}, status=500)
