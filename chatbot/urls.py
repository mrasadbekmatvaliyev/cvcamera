from django.urls import path
from .views import chatbot_view, chat_response

urlpatterns = [
    path('', chatbot_view, name='chatbot'),
    path('api/response/', chat_response, name='chat_response'),
]
