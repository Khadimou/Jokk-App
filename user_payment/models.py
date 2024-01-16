from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group, Permission, User
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings

class AppUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('An email is required.')
        if not password:
            raise ValueError('A password is required.')
        email = self.normalize_email(email)
        user = self.model(email=email)
        user.set_password(password)
        user.save()
        return user
    def create_superuser(self, email, password=None):
        if not email:
            raise ValueError('An email is required.')
        if not password:
            raise ValueError('A password is required.')
        user = self.create_user(email, password)
        user.is_superuser = True
        user.save()
        return user

class AppUser(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_premium = models.BooleanField(default=False)
    country = models.CharField(max_length=100)
    failed_payment_attempts = models.IntegerField(default=0)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)  # Ajouté pour gérer l'ID de l'abonnement Stripe

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_or_update_appuser(sender, instance, created, **kwargs):
    if created:
        AppUser.objects.create(user=instance)
    app_user = AppUser.objects.get(user=instance)
    # Synchroniser les champs supplémentaires si nécessaire
    # Par exemple, si vous avez d'autres champs dans AppUser qui doivent être synchronisés
    app_user.save()

class UserPayment(models.Model):
    app_user = models.ForeignKey(AppUser, on_delete=models.CASCADE)
    payment_bool = models.BooleanField(default=False)
    stripe_checkout_id = models.CharField(max_length=500)
    # Ajouté pour gérer les paiements liés aux abonnements
    stripe_subscription_payment = models.BooleanField(default=False)

@receiver(post_save, sender=AppUser)
def create_user_payment(sender, instance, created, **kwargs):
    if created:
        UserPayment.objects.create(app_user=instance)
