from django.urls import path
from .views import GetPaymentLinkView, StripeWebhookView, PaymentSuccessView, PaymentCancelView

urlpatterns = [
    path('get-link/', GetPaymentLinkView.as_view(), name='get_payment_link'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('success/', PaymentSuccessView.as_view(), name='success'),
    path('cancel/', PaymentCancelView.as_view(), name='cancel'),
]
