from django.db import models
from django.utils import timezone
import uuid

class ChatSession(models.Model):
    """Model to store chat sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    guesty_session_id = models.CharField(max_length=100, unique=True, db_index=True, blank=True, null=True)
    title = models.CharField(max_length=200, default="New Chat")
    message_count = models.IntegerField(default=0)
    last_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} ({self.guesty_session_id})"


class ChatMessage(models.Model):
    """Model to store individual chat messages"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
