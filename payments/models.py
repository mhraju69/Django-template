from django.db import models
from bookings.models import *
from django.utils import timezone
from django.conf import settings
# Create your models here.

class Payments(models.Model):
    STATUS = (
        ('pending','Pending'),
        ('paid','Paid'),
        ('failed','Failed'),
    )
    booking = models.ForeignKey(Booking,on_delete=models.SET_NULL,blank=True,null=True)
    service = models.ForeignKey(Service,on_delete=models.SET_NULL,blank=True,null=True)
    client = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,blank=True,null=True)
    amount = models.FloatField()
    payment_date = models.DateTimeField(default=timezone.now)
    payment_status = models.CharField(max_length=20,choices=STATUS,default='pending')
    transaction_id = models.CharField(max_length=20)
    invoice_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.booking.booking_id} - {self.payment_status} - {self.amount} - {self.client.email}"

