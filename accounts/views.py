from .models import *
from .helper import *
from .serializers import *
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status,permissions
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.

class SignUpView(generics.CreateAPIView):
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "status": True,
            "log": UserProfileSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

    
class SignInView(generics.CreateAPIView):
    serializer_class = SignInSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            "status": True,
            "log": UserProfileSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_object(self):
        return User.objects.filter(email=self.request.user.email).first()


class GetOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        task = request.data.get('task', '')
        if not email:
            return Response(
                {"status": False,"log": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        res = send_otp(email, task)

        if res['status']:
            return Response({"status": True, "log": res['log']}, status=status.HTTP_200_OK)
        else:
            return Response({"status": False,"log": res['log']}, status=status.HTTP_400_BAD_REQUEST)


class OtpVerifyView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')

        if not email or not otp_code:
            return Response(
                {"status": False,"log": "Email and OTP code are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = verify_otp(email, otp_code)

        if result['status']:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"status": False,"log": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "log": UserProfileSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        else:
            # 403 for lock, 400 for invalid/expired
            status_code = status.HTTP_403_FORBIDDEN if "Too many attempts" in result['log'] else status.HTTP_400_BAD_REQUEST
            return Response({"status": False, "log": result['log']}, status=status_code)


class ResetPassword(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')

        if not email or not new_password :
            return Response(
                {"error": "Email and new password are required."},
                status=400
            )
        
        elif request.user.email != email :
            return Response(
                {"error": "You can only reset your own password."},
                status=403)
        
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            return Response({"status": True, "log": "Password reset successfully"}, status=200)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class GetProfileView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):

        token = request.query_params.get('token')

        if not token:
            return Response({'success': False,'log': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user, error = google_login(token)

        if user:
            token = RefreshToken.for_user(user)
            return Response({
                'access': str(token.access_token),
                'refresh': str(token),
                'log': UserProfileSerializer(user, context={'request': request}).data,
                'status': True,
            }, status=status.HTTP_200_OK)
        else:
            return Response({'status': False,'log': error}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class AppleLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        # Handle both JSON (mobile) and Form Data (Apple Redirect)
        identity_token = request.data.get('identity_token') or request.data.get('id_token')
        # Apple sometimes sends user info (name) for the first time
        user_info_raw = request.data.get('user', {}) 
        
        import json
        user_info = {}
        if user_info_raw:
            try:
                user_info = json.loads(user_info_raw) if isinstance(user_info_raw, str) else user_info_raw
            except:
                pass

        if not identity_token:
            return Response({'error': 'No identity token provided'}, status=400)
            
        decoded_token = verify_apple_id_token(identity_token)
        if not decoded_token:
            return Response({'error': 'Invalid identity token'}, status=400)
            
        email = decoded_token.get('email')
        apple_sub = decoded_token.get('sub')  # Apple unique user ID (always present)

        # ✅ "Hide My Email" users এর জন্য sub দিয়ে fallback
        # Apple Private Relay email বা sub-based synthetic email ব্যবহার করো
        if not email:
            if not apple_sub:
                return Response({'error': 'Unable to identify Apple user'}, status=400)
            # sub দিয়ে existing user খোঁজো অথবা synthetic email বানাও
            email = f"apple_{apple_sub}@privaterelay.appleid.com"
            
        # Try to get name from user_info if provided (first time login)
        name = user_info.get('name', {}).get('firstName', '')
        last_name = user_info.get('name', {}).get('lastName', '')
        full_name = f"{name} {last_name}".strip() if name or last_name else email.split('@')[0]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'name': full_name,
                'is_active': True,
                'password': make_password(None)
            }
        )

        if getattr(user, 'block', False):
            return Response(
                {"error": "User account is disabled. Please contact support"},
                status=403
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)
        
        plan = Subscriptions.objects.filter(company=get_company(user)).first()
        session = generate_session(request, user, refresh.access_token)   
        
        # Check if it's a browser/redirect flow (Form Data from Apple)
        if request.content_type == 'application/x-www-form-urlencoded':
            frontend_url = getattr(settings, 'FRONTEND_URL').rstrip('/')
            callback_url = f"{frontend_url}/auth/callback"
            
            params = urllib.parse.urlencode({
                'access': access,
                'refresh': refresh_token,
                'plan': True if plan else False,
                'status': 'success',
            })
            return redirect(f"{callback_url}?{params}")

        # Standard JSON response for mobile/direct API
        serializer = UserSerializer(user, context={'request': request})
        return Response({
            "log": serializer.data, 
            "access": access, 
            "refresh": refresh_token,
            "plan": True if plan else False,
        })

