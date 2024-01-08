from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from django.contrib.auth import views as auth_views

from .views import SearchUsersAPIView

router = DefaultRouter()
router.register(r'messages', views.MessageViewSet)

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('clear-chat/', views.clear_chat, name='clear_chat'),
    path('my-assistants/',views.my_assistants,name='my_assistants'),
    path('api/', include(router.urls)),
    path('api/search-users/', SearchUsersAPIView.as_view(), name='search-users'),
    path('api/send_message/', views.send_message, name='send_message'),
    path('send_reply/', views.send_reply, name='send_reply'),
    path('sendMessage/', views.sendMessage, name='sendMessage'),
    path('messaging/', views.messaging_view, name='messaging'),
    path('conversations/', views.get_conversations, name='conversations'),
    path('messages/<str:username>/', views.get_messages, name='get_messages'),
    path('get_unread_messages_count/',views.get_unread_messages_count,name='get-unread-messages-count'),
    path('mark_message_as_read/<int:message_id>/', views.mark_message_as_read, name='mark_message_as_read'),
    path('mark_conversation_as_read/<str:username>/', views.mark_conversation_as_read, name='mark_conversation_as_read'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home, name='home'),
    path('account/', views.account_settings, name='account_settings'),
    path('delete_account/',views.delete_account, name='delete_account'),
    path('theme/', views.change_theme, name='change_theme'),
    path('profile/',views.create_profile,name='create_profile'),
    path('profile/<int:user_id>/',views.profile_view,name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('searching/', views.searching, name='searching'),
    path('get_user_info', views.get_user_info, name='get_user_info'),
    path('get_user_id', views.get_user_id, name='get_user_id'),
    path('get-message-details/<int:message_id>/', views.message_details, name='message_details_base'),
    path('scrape/', views.scrape_view, name='scrape'),
    path('chat/', views.chat_view, name='chat'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    ]