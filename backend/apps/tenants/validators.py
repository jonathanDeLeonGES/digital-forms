from django.core.validators import RegexValidator

validate_subdomain_format = RegexValidator(
    regex=r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$',
    message=(
        'El subdominio solo puede contener letras minúsculas, dígitos y guiones. '
        'No puede empezar ni terminar con guión.'
    ),
)
