from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'nombre_completo', 'email', 'role', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CreateUserSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=[c[0] for c in CustomUser.ROLES])


class UpdateUserSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=200, required=False)
    email = serializers.EmailField(required=False)
    role = serializers.ChoiceField(choices=[c[0] for c in CustomUser.ROLES], required=False)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'nombre_completo', 'email', 'role', 'is_active', 'created_at']
        read_only_fields = ['id', 'role', 'is_active', 'created_at']


class ProfileUpdateSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=200, required=False)
    email = serializers.EmailField(required=False)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
