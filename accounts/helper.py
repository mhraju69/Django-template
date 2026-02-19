from django.utils import timezone
from datetime import timedelta
from .models import OTP, User
from django.core.mail import send_mail
from django.conf import settings
import json

def send_otp(email, task="verification"):
    try:
        user = User.objects.get(email=email)
        otp_obj = OTP.generate_otp(user)
        
        subject = f"Your OTP for {task}"
        message = f"Your OTP code is {otp_obj.otp}. It will expire in 3 minutes."
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [email]
        
        send_mail(subject, message, email_from, recipient_list)
        
        return {"status": True, "log": f"OTP sent successfully to {email}"}
    except User.DoesNotExist:
        return {"status": False, "log": "User with this email does not exist."}
    except Exception as e:
        return {"status": False, "log": str(e)}


def verify_otp(email, otp_code):
    try:
        otp_obj = OTP.objects.filter(user__email=email).latest('created_at')
    except OTP.DoesNotExist:
        return {"status": False, "log": "Invalid OTP or email."}

    # Check expiry
    if otp_obj.is_expired():
        return {"status": False, "log": "OTP has expired."}

    # Verify OTP
    if otp_obj.otp != otp_code:
        return {"status": False, "log": "Invalid OTP."}

    # OTP verified, activate user & delete OTP
    user = otp_obj.user
    user.is_active = True
    user.save()
    otp_obj.delete()

    return {"status": True, "log": "OTP verified statusfully."}


def google_login(access_token):

    if not access_token:
        return None, "Access token is required"

    try:
        # Validate token
        token_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v3/tokeninfo",
            params={"access_token": access_token},
            timeout=10
        )

        if token_info_response.status_code != 200:
            return None, "Invalid access token"

        # Get user info
        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )

        if user_info_response.status_code != 200:
            return None, "Failed to fetch user info"

        user_data = user_info_response.json()

        email = user_data.get("email")
        name = user_data.get("name")
        profile_image_url = user_data.get("picture")

        if not email:
            return None, "Email not provided by Google"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": name,
                "is_active": True,
                "password": make_password(None),
            },
        )

        # Save profile image
        if created and profile_image_url:
            img_response = requests.get(profile_image_url)
            if img_response.status_code == 200:
                file_name = f"{slugify(name)}-profile.jpg"
                user.image.save(
                    file_name,
                    ContentFile(img_response.content),
                    save=True,
                )

        if getattr(user, "block", False):
            return None, "User account is disabled"

        return user, None

    except Exception as e:
        return None, str(e)


def apple_login(identity_token, user_info_raw):
    try:
        user_info = {}
        if user_info_raw:
            try:
                user_info = json.loads(user_info_raw) if isinstance(user_info_raw, str) else user_info_raw
            except:
                pass

        if not identity_token:
            return Response({'error': 'No identity token provided'}, status=400)
            
        header = jwt.get_unverified_header(identity_token)
        kid = header.get('kid')
        
        # Get Apple's public keys
        apple_keys = requests.get('https://appleid.apple.com/auth/keys').json()
        
        # Find the matching key
        public_key_data = next(key for key in apple_keys['keys'] if key['kid'] == kid)
        public_key = RSAAlgorithm.from_jwk(public_key_data)
        
        # Verify the token
        decoded_token = jwt.decode(
            identity_token,
            public_key,
            algorithms=['RS256'],
            audience=settings.APPLE_CLIENT_ID,
            issuer='https://appleid.apple.com'
        )
                
        if not decoded_token:
            return None, "Invalid identity token"
            
        email = decoded_token.get('email')
        
        if not email:
            return None, "Email not provided by Apple"
            
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

        if getattr(user, "block", False):
            return None, "User account is disabled"

        return user, None

    except Exception as e:
        return None, str(e)

