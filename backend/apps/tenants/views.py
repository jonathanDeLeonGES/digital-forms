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

        d = serializer.validated_data
        try:
            tenant = TenantRegistrationService.register(
                nombre_empresa=d["nombre_empresa"],
                subdominio=d["subdominio"],
                email_admin=d["email_admin"],
                password=d["password"],
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
                "email_admin": d["email_admin"],
                "trial_expires_at": tenant.subscription.fecha_fin,
                "message": "Tenant registrado exitosamente. Ya puedes iniciar sesión.",
            },
            status=201,
        )
