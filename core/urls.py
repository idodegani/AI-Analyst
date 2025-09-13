from django.urls import path
from . import views, api_views

urlpatterns = [
    path('', views.index, name='index'),
    
    # API endpoints
    path('api/sessions/', api_views.get_sessions, name='api_get_sessions'),
    path('api/sessions/create/', api_views.create_session, name='api_create_session'),
    path('api/sessions/<str:session_id>/', api_views.update_session, name='api_update_session'),
    path('api/sessions/<str:session_id>/delete/', api_views.delete_session, name='api_delete_session'),
    path('api/sessions/<str:session_id>/messages/', api_views.get_messages, name='api_get_messages'),
    path('api/messages/send/', api_views.send_message, name='api_send_message'),
]
