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


class FirebaseLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        id_token = request.query_params.get('token')
        oauth = request.query_params.get('oauth',True)

        if not id_token:
            return Response({'status': False,'log': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
        except Exception as e:
            return Response({'status': False,'log': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        
        if not email:
            return Response({'status': False,'log': 'Email not provided by Firebase'}, status=status.HTTP_400_BAD_REQUEST)
            
        name = decoded_token.get('name')
        profile_image_url = decoded_token.get('picture')

        if oauth:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "uid":uid,
                    'name': name,
                    'is_active': True,
                    'password': make_password(None),
                },
            )
            if created and profile_image_url:
                img_response = requests.get(profile_image_url)
                if img_response.status_code == 200:
                    file_name = f"{slugify(name or email.split('@')[0])}-profile.jpg"
                    user.image.save(
                        file_name,
                        ContentFile(img_response.content),
                        save=True,
                    )
        else:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "uid":uid,
                    'name': request.data.get('name') or "",
                    'is_active': False,
                    'password': make_password(uid),
                }
            )
            if not user.is_active:
                send_otp(user.email)

            print(UserProfileSerializer(user, context={'request': request}).data)

        if user:
            token = RefreshToken.for_user(user)
            return Response({
                'access': str(token.access_token),
                'refresh': str(token),
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'status': True,
                'active': user.is_active,
                'log': 'Login successful'
            }, status=status.HTTP_200_OK)
        else:
            return Response({'status': False,'log': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

