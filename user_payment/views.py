from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from user_payment.models import UserPayment, AppUser
import stripe
import time

# @login_required(login_url='login')
# def product_page(request):
#     stripe.api_key = settings.STRIPE_SECRET_KEY_TEST
#     if request.method == 'POST':
#         checkout_session = stripe.checkout.Session.create(
#             payment_method_types = ['card'],
#             line_items = [
#                 {
#                     'price': settings.PRODUCT_PRICE,
#                     'quantity': 1,
#                 },
#             ],
#             mode = 'payment',
#             customer_creation = 'always',
#             success_url = settings.REDIRECT_DOMAIN + '/payment_successful?session_id={CHECKOUT_SESSION_ID}',
#             cancel_url = settings.REDIRECT_DOMAIN + '/payment_cancelled',
#         )
#         return redirect(checkout_session.url, code=303)
#     return render(request, 'user_payment/product_page.html')

@login_required(login_url='login')
def product_page(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY_TEST

    if request.method == 'POST':
        success_url = request.build_absolute_uri(reverse('payment_successful')) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))

        subscription_type = request.POST.get('subscription_type', 'monthly')  # 'weekly' ou 'monthly'

        if subscription_type == 'weekly':
            price_id = settings.WEEKLY_SUBSCRIPTION_PRICE  # ID de prix pour l'abonnement hebdomadaire
        else:
            price_id = settings.MONTHLY_SUBSCRIPTION_PRICE  # ID de prix pour l'abonnement mensuel

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            subscription_data={
                'trial_period_days': 1,
            },
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return redirect(checkout_session.url, code=303)

    return render(request, 'user_payment/product_page.html')

def cancel_page(request):
    return render(request, 'user_payment/cancel_subscription.html')
@login_required(login_url='login')
def cancel_subscription(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY_TEST

    try:
        app_user = request.user.appuser
        subscription_id = app_user.stripe_subscription_id

        if subscription_id and request.method == 'POST':
            # Annuler l'abonnement sur Stripe
            stripe.Subscription.delete(subscription_id)

            # Mettre à jour les informations de l'utilisateur dans la base de données
            app_user.is_premium = False
            app_user.stripe_subscription_id = None
            app_user.save()

            # Rediriger vers une page de confirmation ou de succès
            return redirect('subscription_cancelled_successfully')

        return render(request, 'user_payment/cancel_subscription.html')

    except stripe.error.StripeError as e:
        # Gérer les erreurs Stripe
        return render(request, 'error.html', {'message': str(e)})

## use Stripe dummy card: 4242 4242 4242 4242

def payment_successful(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY_TEST
    checkout_session_id = request.GET.get('session_id', None)

    if not checkout_session_id:
        # Rediriger vers une page d'erreur ou la page d'accueil si l'ID de session est absent
        return redirect('home')

    try:
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        customer = stripe.Customer.retrieve(session.customer)  # Récupérer les informations du client
    except stripe.error.StripeError as e:
        # Gérer l'erreur Stripe (par exemple, session ou client non trouvés)
        return redirect('error_page')

    app_user, created = AppUser.objects.get_or_create(user=request.user)

    if session.mode == 'subscription':
        app_user.is_premium = True
        app_user.stripe_subscription_id = session.subscription  # Enregistrer l'ID d'abonnement
        app_user.save()

    user_payment, created = UserPayment.objects.get_or_create(app_user=app_user)
    user_payment.stripe_checkout_id = checkout_session_id
    user_payment.payment_bool = True
    user_payment.save()

    return render(request, 'user_payment/payment_successful.html', {'customer': customer})
def payment_cancelled(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY_TEST
    return render(request, 'user_payment/payment_cancelled.html')

def subscription_cancelled_successfully(request):
    return render(request, 'user_payment/subscription_cancelled.html')

@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY_TEST
    payload = request.body
    signature_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, signature_header, settings.STRIPE_WEBHOOK_SECRET_TEST
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Retrieve the user payment record
        try:
            user_payment = UserPayment.objects.get(stripe_checkout_id=session.id)
        except UserPayment.DoesNotExist:
            return HttpResponse(status=404)

        if session.mode == 'subscription':
            user_payment.payment_bool = True
            user_payment.stripe_subscription_payment = True
            user_payment.save()

            # Retrieve the corresponding AppUser
            app_user = user_payment.app_user
            app_user.is_premium = True
            app_user.stripe_subscription_id = session.subscription
            app_user.save()

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        try:
            app_user = AppUser.objects.get(stripe_subscription_id=subscription.id)
            app_user.is_premium = False
            app_user.stripe_subscription_id = None
            app_user.save()
        except AppUser.DoesNotExist:
            pass  # Subscription not found
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        try:
            app_user = AppUser.objects.get(stripe_subscription_id=subscription.id)
            app_user.is_premium = subscription.status == 'active'
            app_user.save()
        except AppUser.DoesNotExist:
            pass

    return HttpResponse(status=200)
