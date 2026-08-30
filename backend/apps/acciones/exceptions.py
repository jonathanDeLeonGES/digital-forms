from rest_framework.exceptions import ValidationError


class InvalidTransitionError(ValidationError):
    def __init__(self, desde, hacia):
        validos = ', '.join(
            _valid_targets(desde)
        ) or 'ninguna'
        detail = (
            f"Transición inválida: '{desde}' → '{hacia}'. "
            f"Transiciones disponibles desde '{desde}': {validos}."
        )
        super().__init__(detail={'detail': detail})


def _valid_targets(estado):
    from apps.acciones.models import Accion
    return Accion.TRANSICIONES_VALIDAS.get(estado, [])
