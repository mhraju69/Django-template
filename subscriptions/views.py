from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny
from .models import *
from .serializers import *


class GetPlans(APIView):
    permission_classes = [AllowAny]
    serializer_class = PlanSerializers

    def get(self, request):
        plans = Plan.objects.all()
        serializer = self.serializer_class(plans, many=True)  
        return Response({"status":True , "log": serializer.data})