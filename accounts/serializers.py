from .models import User
from rest_framework import serializers


class SignUpSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Password fields do not match.")
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data.get('name', ''),
            password=validated_data['password']
        )
        return user


class SignInSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password']
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = User.objects.filter(email=email).first()
            if user:
                if not user.check_password(password):
                     raise serializers.ValidationError("Invalid credentials")
                if not user.is_active:
                    raise serializers.ValidationError("User is not active")
                if user.block:
                    raise serializers.ValidationError("User is blocked")
                attrs['user'] = user
                return attrs
            else:
                raise serializers.ValidationError("User not found")
        raise serializers.ValidationError("Email and password are required")


class UserProfileSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ['id', 'email', 'role']

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)

        if validated_data.get('password'):
            if not instance.check_password(validated_data['old_password']):
                raise serializers.ValidationError("Old password does not match.")
            instance.set_password(validated_data['password'])

        instance.save()
        return instance
