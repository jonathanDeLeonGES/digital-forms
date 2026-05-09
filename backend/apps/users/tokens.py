from django.db import connection
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user) -> RefreshToken:
        token = super().get_token(user)
        token['role'] = user.role
        token['tenant'] = connection.schema_name
        return token
