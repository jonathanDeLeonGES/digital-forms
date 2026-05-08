from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import SubdomainAlreadyExistsError
from .serializers import TenantRegistrationSerializer
from .services import TenantRegistrationService


class TenantRegistrationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = TenantRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            tenant = TenantRegistrationService.register(
                nombre_empresa=serializer.validated_data["nombre_empresa"],
                subdominio=serializer.validated_data["subdominio"],
                email_admin=serializer.validated_data["email_admin"],
            )
        except SubdomainAlreadyExistsError as e:
            return Response(
                {"detail": str(e), "code": "subdomain_already_exists"},
                status=409,
            )

        return Response(
            {
                "id": tenant.id,
                "subdominio": tenant.schema_name,
                "trial_expires_at": tenant.subscription.fecha_fin,
                "message": "Tenant registrado exitosamente.",
            },
            status=201,
        )
