from django.urls import path
from . import views

urlpatterns = [
    path('product_page/', views.product_page, name='product_page'),
    path('subscription_management/', views.subscription_management, name='subscription_management'),
    path('payment_successful/', views.payment_successful, name='payment_successful'),
    path('payment_cancelled/', views.payment_cancelled, name='payment_cancelled'),
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('cancel-subscription/',views.cancel_subscription,name='cancel_subscription'),
    path('cancel/',views.cancel_page,name='cancel_page'),
    path('subscription-cancelled-successfully/', views.subscription_cancelled_successfully, name='subscription_cancelled_successfully'),
]
