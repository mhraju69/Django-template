from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
# Create your models here.


class Plan(models.Model):
    PLAN = [
        ("essential", "Essential"),
        ("growth", "Growth"),
        ("enterprise", "Enterprise Custom"),
    ]
    DURATION = [
        ("months", "Monthly"),
        ("years", "Yearly"),
    ]

    name = models.CharField(max_length=20, choices=PLAN)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=20, choices=DURATION)
    
    def __str__(self):
        return f"{self.get_name_display()} ({self.get_duration_display()})"

    def save(self, *args, **kwargs):
        if self.name in ["essential", "growth"]:
            existing = Plan.objects.filter(
                name=self.name,
                duration=self.duration,
            ).exclude(id=self.id)

            if existing.exists():
                raise ValidationError(
                    f"A default plan with name '{self.name}' already exists."
                )

        super().save(*args, **kwargs)


class Subscriptions(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='subscriptions', on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.start:
            self.start = timezone.now()

        plan_obj = self.plan

        if not self.end and plan_obj:

            if plan_obj.duration == 'months':
                self.end = self.start + relativedelta(months=1)

            elif plan_obj.duration == 'years':
                self.end = self.start + relativedelta(years=1)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.plan.name}"

