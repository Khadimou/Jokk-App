from django.urls  import path

from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home, name='home'),
    path('account/', views.account_settings, name='account_settings'),
    path('delete_account/',views.delete_account, name='delete_account'),
    path('theme/', views.change_theme, name='change_theme'),
    path('profile/',views.create_profile,name='create_profile'),
    path('profile/<int:user_id>/',views.profile_view,name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('search/', views.search_view, name='search_view'),
    path('scrape/', views.scrape_view, name='scrape'),
    path('chat/', views.chat_view, name='chat'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    ]