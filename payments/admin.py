from django.contrib import admin
from .models import Payments
from unfold.admin import ModelAdmin
# Register your models here.

admin.site.register(Payments, ModelAdmin)