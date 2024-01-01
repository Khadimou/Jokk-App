from django.urls  import path

from . import views


urlpatterns = [
    path('revision_group/',views.revision_group,name='revision_group'),
    path('assistant-endpoint/<int:workgroup_id>/', views.assistant_endpoint, name='assistant_endpoint'),
    path('search',views.search_view,name='search'),
    path('send_invitation/', views.send_invitation, name='send_invitation'),
    path('get-notifications/', views.get_notifications, name='get-notifications'),
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('mark_notification_as_read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/clear_all/', views.clear_all_notifications, name='clear_all_notifications'),
    path('join_workgroup/<int:workgroup_id>/',views.join_workgroup,name='join_workgroup'),
    path('workgroups/<int:pk>/accept-invitation/', views.accept_invitation, name='accept_invitation'),
    path('workgroups/<int:pk>/refuse-invitation/', views.refuse_invitation, name='refuse_invitation'),
    path('notifications/accept-join/<int:notification_id>/', views.accept_join, name='accept_join'),
    path('notifications/deny-join/<int:notification_id>/', views.deny_join, name='deny_join'),
    path('create-workgroup/', views.create_workgroup, name='create_workgroup'),
    path('workgroups/<int:pk>/', views.workgroup_detail, name='workgroup_detail'),
    path('edit_workgroup/<int:pk>/', views.edit_workgroup, name='edit_workgroup'),
    path('workgroups/', views.workgroup_list, name='workgroup_list'),
    path('delete_workgroup/<int:pk>/', views.delete_workgroup, name='delete_workgroup'),
    path('workgroups/<int:workgroup_id>/create-chat/', views.create_chat_room, name='create_chat_room'),
    path('chat-room/<int:chat_room_id>/', views.chat_room, name='chat_room'),
]
