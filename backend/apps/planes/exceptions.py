from rest_framework.exceptions import ValidationError


class InvalidEstadoError(ValidationError):
    def __init__(self, desde, hacia):
        detail = (
            f"Transición inválida: '{desde}' → '{hacia}'. "
            "Estados válidos: pendiente, en_proceso, completada."
        )
        super().__init__(detail={'detail': detail})


class LastActividadError(ValidationError):
    def __init__(self):
        super().__init__(detail={'detail': 'El plan debe tener al menos una actividad.'})
