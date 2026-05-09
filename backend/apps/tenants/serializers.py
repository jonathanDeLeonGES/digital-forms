from rest_framework import serializers

from .validators import validate_subdomain_format


class TenantRegistrationSerializer(serializers.Serializer):
    nombre_empresa = serializers.CharField(max_length=200)
    subdominio = serializers.CharField(max_length=63, validators=[validate_subdomain_format])
    email_admin = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
