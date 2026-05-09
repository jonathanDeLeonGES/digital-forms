from rest_framework.exceptions import ValidationError


class InvalidTransitionError(ValidationError):
    def __init__(self, desde, hacia):
        detail = (
            f"Transición inválida: '{desde}' → '{hacia}'. "
            f"Transiciones disponibles desde '{desde}': "
            f"{_valid_targets(desde) or 'ninguna'}."
        )
        super().__init__(detail={'detail': detail})


def _valid_targets(estado):
    from apps.issues.models import Issue
    return ', '.join(Issue.TRANSICIONES_VALIDAS.get(estado, []))
