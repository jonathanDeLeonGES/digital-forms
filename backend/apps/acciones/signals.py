from django.dispatch import Signal

accion_estado_cambiado = Signal()
# Kwargs: accion, estado_anterior, estado_nuevo, usuario, timestamp
