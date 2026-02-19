from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('signin/', SignInView.as_view(), name='signin'),
    path('user/', UserRetrieveUpdateDestroyView.as_view(), name='user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-otp/', OtpVerifyView.as_view(), name='verify_otp'),
    path('get-otp/', GetOtpView.as_view(), name='get_otp'),
    path('reset-password/', ResetPassword.as_view(), name='reset_password'),
    path('profile/', GetProfileView.as_view(), name='get_profile'),
    path('google/login/', GoogleLoginView.as_view(), name='google_login'),
    path('apple/login/', AppleLoginView.as_view(), name='apple_login'),
]