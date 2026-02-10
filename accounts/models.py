from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.conf import settings
import random
from django.utils import timezone
from datetime import timedelta

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE = (('parent', 'Parent'),('child', 'Child'),('admin', 'Admin'),)
    email = models.EmailField(max_length=255,unique=True,verbose_name="User Email")
    name = models.CharField(max_length=200, blank=True, null=True,verbose_name="User Name")
    bio = models.TextField(blank=True, null=True,verbose_name="User Bio")
    cover = models.ImageField(upload_to='cover_images/', blank=True, null=True,)
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True,)
    role = models.CharField(max_length=10, choices=ROLE, default='parent',verbose_name="User Role")
    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='children',)
    is_active = models.BooleanField(default=False,verbose_name="Active User")
    is_staff = models.BooleanField(default=False,verbose_name="Staff User")
    is_superuser = models.BooleanField(default=False,verbose_name="Super User")  
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Joining Date")
    block = models.BooleanField(default=False,verbose_name="Suspend User")

    objects = UserManager()
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
        
    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_sha256$'):
            self.set_password(self.password)

        if self.is_staff and self.is_superuser:
            self.role = 'admin'

        if self.role == 'parent':
            self.parent = None

        if self.role == 'child' and self.parent is None:
            raise ValueError("Child users must have a parent assigned")

        super().save(*args, **kwargs)

    @property
    def is_parent(self):
        return self.role == 'parent'

    @property
    def is_child(self):
        return self.role == 'child'


class OTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='user_otp',  
        on_delete=models.CASCADE
    )
    otp = models.CharField(max_length=6,verbose_name="OTP Code")
    created_at = models.DateTimeField(auto_now_add=True)
    attempt_count = models.IntegerField(default=0)  
    last_tried = models.DateTimeField(null=True, blank=True)  

    def __str__(self):
        return f"OTP for: {self.user}."

    @staticmethod
    def generate_otp(user):
        otp_code = str(random.randint(1000, 9999))
        return OTP.objects.create(user=user, otp=otp_code)

    def is_expired(self):
        return self.created_at + timedelta(minutes=3) < timezone.now()


