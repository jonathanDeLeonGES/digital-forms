from django.http import JsonResponse


class AccessPolicyMiddleware:
    WHITELIST = ("/admin/", "/api/public/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)

        if tenant is None:
            return self.get_response(request)

        if any(request.path.startswith(prefix) for prefix in self.WHITELIST):
            return self.get_response(request)

        if not tenant.subscription.is_active():
            return JsonResponse(
                {
                    "detail": (
                        "Tu suscripción ha vencido. "
                        "Contacta al administrador para renovarla."
                    ),
                    "code": "trial_expired",
                },
                status=402,
            )

        return self.get_response(request)
