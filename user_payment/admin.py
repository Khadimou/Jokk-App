from django.contrib import admin

from user_payment.models import UserPayment, AppUser

# Register your models here.
admin.site.register(AppUser)
admin.site.register(UserPayment)