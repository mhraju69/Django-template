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
            "user": UserProfileSerializer(user).data,
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
            "user": UserProfileSerializer(user).data,
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
                "user": UserProfileSerializer(user).data,
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
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'status': True,
                'log': 'Login successful'
            }, status=status.HTTP_200_OK)
        else:
            return Response({'status': False,'log': error}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class AppleLoginView(APIView):

    permission_classes = [permissions.AllowAny]
    def post(self, request):
        identity_token = request.data.get('identity_token') or request.data.get('id_token')
        user_info_raw = request.data.get('user', {}) 
        
        user , error = apple_login(identity_token, user_info_raw)        

        if user:
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            refresh_token = str(refresh)
        else:
            return Response({'status': False,'log': error}, status=status.HTTP_400_BAD_REQUEST)

        # Check if it's a browser/redirect flow (Form Data from Apple)
        if request.content_type == 'application/x-www-form-urlencoded':
            frontend_url = getattr(settings, 'FRONTEND_URL', 'https://wahejan.vercel.app').rstrip('/')
            callback_url = f"{frontend_url}/auth/callback"
            
            params = urllib.parse.urlencode({
                'access': access,
                'refresh': refresh_token,
                'status': True,
                'log': 'Login successful'
            })
            return redirect(f"{callback_url}?{params}")

        return Response({
            "access": access, 
            "refresh": refresh_token, 
            "user": UserProfileSerializer(user, context={'request': request}).data,
            "status": True,
            "log": "Login successful"
        })


