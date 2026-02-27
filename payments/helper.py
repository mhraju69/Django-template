# helper.py
import stripe
from django.conf import settings
from django.urls import reverse
stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(request, booking , payment , price, customer=None ):

    if booking is None or price is None or payment is None:
        raise Exception("Required data for Checkout Session is missing")
    
    session_data = {
        "payment_method_types": ["card"],
        "mode": "payment",
        "line_items": [
            {
                "price_data": {
                    "currency": "eur",
                    "unit_amount": int(price * 100),
                    "product_data": {
                        "name": "Confirm your booking",
                    },
                },
                "quantity": 1 ,
            }
        ],
        "success_url": request.build_absolute_uri(reverse("success")),
        "cancel_url": request.build_absolute_uri(reverse("cancel")),
        "invoice_creation": {
            "enabled": True,
        },
        "metadata": {
            "booking": str(booking),
            "payment": str(payment)
        },
        "payment_intent_data": {
            "metadata": {
                "booking": str(booking),
                "payment": str(payment)
            }
        },
        "invoice_creation": {
            "enabled": True,
            "invoice_data": {
                "metadata": {
                    "booking": str(booking),
                    "payment": str(payment)
                }
            }
        }
    }
    
    if customer:
        session_data["customer"] = customer

    session = stripe.checkout.Session.create(**session_data)

    return session.url


def create_payment_intent_data(request, booking , payment , price , customer_email , method="web"):

    if booking is None or price is None or payment is None:
        raise Exception("Required payment data (booking, price, or payment ID) is missing")
    
    # Check if customer exists in Stripe or create new
    customers = stripe.Customer.list(email=customer_email).data
    if customers:
        customer = customers[0]
    else:
        customer = stripe.Customer.create(email=customer_email)
    
    if method == "web":
        return create_checkout_session(request, booking, payment, price, customer=customer.id)
    
    # Create CustomerSession
    # components={"mobile_payment_element": {"enabled": True}} is for Mobile Payment Element
    customer_session = stripe.CustomerSession.create(
        customer=customer.id,
        components={"mobile_payment_element": {
            "enabled": True,
            "features": {
                "payment_method_save": "enabled",
                "payment_method_redisplay": "enabled",
                "payment_method_remove": "enabled"
            }
        }}
    )
    
    # Create PaymentIntent
    payment_intent = stripe.PaymentIntent.create(
        amount=int(price * 100),
        currency='eur',
        customer=customer.id,
        automatic_payment_methods={'enabled': True},
        metadata={
            "booking": str(booking),
            "payment": str(payment) 
        }
    )
    
    return {
        "paymentIntent": payment_intent.client_secret,
        "customerSessionClientSecret": customer_session.client_secret,
        "customer": customer.id,
        "publishableKey": settings.STRIPE_PUBLISHABLE_KEY
    }

