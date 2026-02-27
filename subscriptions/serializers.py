from rest_framework import serializers
from .models import *

class PlanSerializers(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id','name', 'duration', 'price','msg_limit','user_limit','token_limit', 'custom']
        
class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.get_name_display', read_only=True)
    plan_duration = serializers.CharField(source='plan.get_duration_display', read_only=True)
    plan_price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Subscriptions
        fields = ['id', 'company', 'plan', 'plan_name', 'plan_duration', 'plan_price', 'start', 'end', 'auto_renew', 'active']
        read_only_fields = ['company', 'start', 'end', 'active']