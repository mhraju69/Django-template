import stripe
import json
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Payments
from .serializers import PaymentSerializer
from .helper import create_payment_intent_data
from bookings.models import Booking

# Create your views here.

class GetPaymentLinkView(APIView):
    
    def post(self, request):
        method = request.query_params.get("method", "web")
        booking_id = request.data.get("booking_id")
        
        if not booking_id:
            return Response({"error": "Booking ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        # Payment record search or create
        payment = Payments.objects.create(
            booking=booking,
            client=booking.user,
            service=booking.service,
            amount=float(booking.price),
            payment_status='pending'
        )

        try:
            # Payment link or secret data creation
            payment_data = create_payment_intent_data(
                request, 
                booking=booking.id, 
                payment=payment.id, 
                price=float(payment.amount), 
                customer_email=booking.user.email,
                method=method
            )

            return Response({
                "status": True,
                "log": payment_data
            })
        except Exception as e:
            # Delete the pending payment if link creation fails to avoid duplicates
            payment.delete()
            return Response({
                "status": False,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class PaymentSuccessView(APIView):
    permission_classes = []
    def get(self, request):
        return Response({"message": "Payment successful! Your booking is confirmed."})

class PaymentCancelView(APIView):
    permission_classes = []
    def get(self, request):
        return Response({"message": "Payment cancelled."})


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        print("!!! Webhook Path Hit Successfully !!!")
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        print("--- Stripe Webhook Received ---")
        # print(f"Payload: {payload[:100]}...") # Limit log size

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            print(f"Event Verified: {event['type']}")
        except ValueError as e:
            print(f"Invalid payload: {str(e)}")
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            print(f"Invalid signature: {str(e)}")
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

        if event['type'] in ['checkout.session.completed', 'payment_intent.succeeded', 'invoice.paid']:
            stripe_obj = event['data']['object']
            metadata = stripe_obj.get('metadata', {})
            
            if not metadata.get('booking'):
                if stripe_obj.get('invoice'):
                    try:
                        inv = stripe.Invoice.retrieve(stripe_obj.get('invoice'))
                        metadata = inv.get('metadata', {})
                    except: pass
                
                if not metadata.get('booking') and stripe_obj.get('payment_intent'):
                    try:
                        pi = stripe.PaymentIntent.retrieve(stripe_obj.get('payment_intent'))
                        metadata = pi.get('metadata', {})
                    except: pass

            booking_id = metadata.get('booking')
            payment_id = metadata.get('payment')
            transaction_id = stripe_obj.get('id')

            print(f"Processing Event: {event['type']} | Booking: {booking_id} | Payment: {payment_id}")

            if booking_id and payment_id:
                try:
                    booking = Booking.objects.get(id=booking_id)
                    payment = Payments.objects.get(id=payment_id)
                    print(f"Update Start: Booking {booking.id}")
                    
                    payment.payment_status = 'paid'
                    payment.transaction_id = transaction_id
                    
                    # --- Multi-step Invoice/Receipt URL Retrieval ---
                    invoice_url = payment.invoice_url or "" # Keep existing URL if any
                    
                    # If the event object IS an invoice, get the URL directly
                    if stripe_obj.get('object') == 'invoice':
                        invoice_url = stripe_obj.get('hosted_invoice_url') or stripe_obj.get('invoice_pdf') or invoice_url

                    # Only fetch if we don't have a URL yet
                    if not invoice_url:
                        invoice_id = stripe_obj.get('invoice')
                        
                        # 1. Try to fetch from Stripe Invoice
                        if invoice_id:
                            try:
                                print(f"Fetching invoice from Stripe: {invoice_id}")
                                inv = stripe.Invoice.retrieve(invoice_id)
                                invoice_url = inv.get('hosted_invoice_url') or inv.get('invoice_pdf') or invoice_url
                            except Exception as e:
                                print(f"Stripe webhook - Error fetching invoice: {e}")

                        # 2. Fallback: Try to fetch receipt_url from the charge (via PaymentIntent)
                        if not invoice_url:
                            pi_id = stripe_obj.get('payment_intent') or (stripe_obj.get('id') if stripe_obj.get('object') == 'payment_intent' else None)
                            if pi_id:
                                try:
                                    pi = stripe.PaymentIntent.retrieve(pi_id)
                                    charge_id = pi.get('latest_charge')
                                    if charge_id:
                                        charge = stripe.Charge.retrieve(charge_id)
                                        invoice_url = charge.get('receipt_url') or invoice_url
                                        print(f"Fetched Receipt URL from Charge: {invoice_url}")
                                except Exception as e:
                                    print(f"Stripe webhook - Error fetching receipt: {e}")

                        # 3. Last Fallback: Use success_url or placeholder
                        if not invoice_url:
                            invoice_url = stripe_obj.get('success_url') or invoice_url

                    payment.invoice_url = invoice_url
                    payment.save()
                    
                    # Update Booking details
                    booking.payment_status = 'paid'
                    booking.status = 'confirmed'
                    booking.save()
                    print(f"!!! Success !!! Booking {booking_id} updated with Invoice URL: {invoice_url}")
                    
                except Exception as e:
                    print(f"Database update error: {str(e)}")
            else:
                print(f"Skipping: Metadata missing for {event['type']}. Available metadata: {metadata}")
        else:
            print(f"Ignoring event type: {event['type']}")

        return HttpResponse(status=status.HTTP_200_OK)