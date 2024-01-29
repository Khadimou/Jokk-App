from django.urls  import path

from . import views


urlpatterns = [
    path('mentoring_page/',views.mentoring_page,name='mentoring_page'),
    path('user_request/<int:notification_id>/', views.user_request_view, name='user_request'),
    path('register_page/',views.register_page,name='register_page'),
    path('send_request/', views.send_request, name='send_request'),
    path('result/', views.result_page, name='result_page'),
    path('evaluate/', views.evaluate_answers, name='evaluate'),
    path('waiting/', views.waiting_page, name='waiting'),
    path('notifications/', views.all_notifications, name='all_notifications'),
    path('matching_optimized/', views.optim_find, name='matching_optim'),
    path('mentee_page/', views.mentee_page, name='mentee_page'),
    path('mentor_page/', views.mentor_page, name='mentor_page'),
    path('redirect_mentor/', views.redirect_mentor, name='redirect_mentor'),
    path('my_page/', views.my_page, name='my_page'),
    path('coaching_request/<int:request_id>/', views.coaching_request, name='coaching_request'),
    path('availability/', views.availability_view, name='availability_view'),
    path('availability_dates',views.availability_dates,name='availability_dates'),
    path('delete_availability/<int:slot_id>/', views.delete_availability, name='delete_availability'),
    ]
