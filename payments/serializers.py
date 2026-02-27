from rest_framework import serializers
from .models import *

class PaymentSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    booking = serializers.SerializerMethodField()
    
    class Meta:
        model = Payments
        fields = '__all__'

    def get_client(self, obj):
        return {
            "name": obj.client.name or None,
            "email": obj.client.email,
        }

    def get_service(self, obj):
        return {
            "name": obj.service.title,
            "duration": obj.service.duration,
        }

    def get_booking(self, obj):
        return {
            "booking_id": obj.booking.booking_id,
            "time_slot": obj.booking.time_slot,
            "booking_capacity": obj.booking.capacity,
        }