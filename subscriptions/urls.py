from django.urls import path
from .views import *


urlpatterns = [
    path('plans/', GetPlans.as_view(), name='plans'),
]

