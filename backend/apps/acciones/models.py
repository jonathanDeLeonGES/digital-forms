from django.db import models


class Accion(models.Model):
    TIPOS = [
        ('correctiva', 'Correctiva'),
        ('preventiva', 'Preventiva'),
        ('mejora', 'De Mejora'),
    ]
    ESTADOS = [
        ('abierto', 'Abierto'),
        ('en_proceso', 'En Proceso'),
        ('cerrado', 'Cerrado'),
        ('verificado', 'Verificado'),
    ]
    TRANSICIONES_VALIDAS = {
        'abierto': ['en_proceso'],
        'en_proceso': ['cerrado'],
        'cerrado': ['verificado'],
        'verificado': [],
    }
    ROLES_TRANSICION = {
        ('abierto', 'en_proceso'): 'responsable_asignado',
        ('en_proceso', 'cerrado'): 'supervisor',
        ('cerrado', 'verificado'): 'verificador',
    }

    issue = models.ForeignKey(
        'issues.Issue', on_delete=models.PROTECT, related_name='acciones'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    resultado_esperado = models.TextField()
    responsable = models.ForeignKey(
        'users.CustomUser', on_delete=models.PROTECT, related_name='acciones_asignadas'
    )
    responsable_temporal = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acciones_responsable_temporal',
    )
    responsable_temporal_hasta = models.DateField(null=True, blank=True)
    fecha_limite = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierto')
    created_by = models.ForeignKey(
        'users.CustomUser', on_delete=models.PROTECT, related_name='acciones_creadas'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_limite']),
            models.Index(fields=['responsable']),
            models.Index(fields=['issue']),
        ]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.resultado_esperado[:60]}"


class HistorialEstado(models.Model):
    accion = models.ForeignKey(
        Accion, on_delete=models.CASCADE, related_name='historial_estados'
    )
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    usuario = models.ForeignKey('users.CustomUser', on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Accion #{self.accion_id}: {self.estado_anterior} → {self.estado_nuevo}"
