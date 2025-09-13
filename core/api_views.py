import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import ChatSession, ChatMessage
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_cloud_services import LlamaCloudIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage as LlamaChatMessage
import logging

logger = logging.getLogger(__name__)

# Configuration - these should be in environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "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")
LLAMA_CLOUD_API_KEY = os.environ.get("LLAMA_CLOUD_API_KEY", "llx-hgbCEzLC1FOiv2hs7ldeHVzdtfOLPmIx9RQyBOzW4Mer611L")
LLAMA_CLOUD_INDEX_NAME = os.environ.get("LLAMA_CLOUD_INDEX_NAME", "GSTY_INDEX")
LLAMA_CLOUD_PROJECT_NAME = os.environ.get("LLAMA_CLOUD_PROJECT_NAME", "Default")
LLAMA_CLOUD_ORGANIZATION_ID = os.environ.get("LLAMA_CLOUD_ORGANIZATION_ID", "acd2b482-30f4-461d-a101-0190a08b0a87")

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Initialize Settings
Settings.llm = OpenAI(model="gpt-4o", temperature=0.1)

# Global variable to store the index connection
_llama_index = None

def get_llama_index():
    """Get or create the LlamaCloud index connection"""
    global _llama_index
    if _llama_index is None:
        try:
            _llama_index = LlamaCloudIndex(
                name=LLAMA_CLOUD_INDEX_NAME,
                project_name=LLAMA_CLOUD_PROJECT_NAME,
                organization_id=LLAMA_CLOUD_ORGANIZATION_ID,
                api_key=LLAMA_CLOUD_API_KEY,
            )
            logger.info("Successfully connected to LlamaCloud index.")
        except Exception as e:
            logger.error(f"Failed to connect to LlamaCloud index: {e}")
            raise
    return _llama_index


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
            messages_data.append({
                'id': str(message.id),  # Convert UUID to string for frontend
                'session_id': session_id,
                'content': message.content,
                'role': message.role,
                'timestamp': message.timestamp.isoformat()
            })
        
        return JsonResponse({'messages': messages_data})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Send a message and get AI response"""
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
        
        # Get all previous messages for context
        previous_messages = session.messages.all().order_by('timestamp')
        
        # Convert to LlamaIndex ChatMessage format
        chat_history = []
        for msg in previous_messages:
            if msg.id != user_message.id:  # Don't include the current message
                chat_history.append(
                    LlamaChatMessage(
                        role=msg.role,
                        content=msg.content
                    )
                )
        
        # Create memory buffer with chat history
        memory = ChatMemoryBuffer.from_defaults(
            chat_history=chat_history,
            token_limit=3900
        )
        
        # Get LlamaCloud index
        index = get_llama_index()
        
        # Create chat engine with memory
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=memory,
            system_prompt=(
                "You are an expert property management assistant for Guesty. "
                "You help property managers with questions about guest communication, "
                "pricing strategies, automation, occupancy optimization, and general "
                "property management best practices. Answer questions based on the "
                "provided context and conversation history."
            ),
        )
        
        # Get AI response
        response = chat_engine.chat(content)
        ai_response_text = str(response)
        
        # Save AI response
        ai_message = ChatMessage.objects.create(
            session=session,
            content=ai_response_text,
            role='assistant'
        )
        
        # Update session metadata
        session.message_count = session.messages.count()
        session.last_message = content[:100]
        if session.message_count == 2:  # First exchange
            session.title = content[:50]
        session.save()
        
        # Return both messages
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
                'timestamp': ai_message.timestamp.isoformat()
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
