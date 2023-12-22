from django.urls  import path

from . import views


urlpatterns = [
    path('mentoring_page/',views.mentoring_page,name='mentoring_page'),
    path('register_page/',views.register_page,name='register_page'),
    path('result/', views.result_page, name='result_page'),
    path('evaluate/', views.evaluate_answers, name='evaluate'),
    path('waiting/', views.waiting_page, name='waiting'),
    path('notifications/', views.all_notifications, name='all_notifications'),
    path('matching_optimized/', views.optim_find, name='matching_optim'),
    path('mentee_page/', views.mentee_page, name='mentee_page'),
    path('mentor_page/', views.mentor_page, name='mentor_page'),
    ]