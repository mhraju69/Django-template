from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
# Register your models here.
admin.site.register(Plan,ModelAdmin)
admin.site.register(Payment,ModelAdmin)
admin.site.register(Subscriptions,ModelAdmin)
