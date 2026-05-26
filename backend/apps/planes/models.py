"""
Modelos para planes-trabajo (Task 1.1).
PlanTrabajo, Actividad, Evidencia con TenantModel pattern.
"""
from django.db import models


class PlanTrabajo(models.Model):
    accion = models.OneToOneField(
        'acciones.Accion',
        on_delete=models.CASCADE,
        related_name='plan_trabajo',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['accion'], name='planes_plan_accion_idx'),
        ]

    @property
    def progreso(self) -> int:
        """Porcentaje de actividades completadas. 0 si no hay actividades."""
        total = self.actividades.count()
        if total == 0:
            return 0
        completadas = self.actividades.filter(estado='completada').count()
        return round((completadas / total) * 100)

    def __str__(self):
        return f"PlanTrabajo #{self.pk} (Accion #{self.accion_id})"


class Actividad(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
    ]

    plan = models.ForeignKey(
        PlanTrabajo,
        on_delete=models.CASCADE,
        related_name='actividades',
    )
    descripcion = models.TextField()
    responsable = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.PROTECT,
        related_name='actividades_asignadas',
    )
    fecha_limite = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['plan'], name='planes_act_plan_idx'),
            models.Index(fields=['fecha_limite'], name='planes_act_fecha_limite_idx'),
            models.Index(fields=['estado'], name='planes_act_estado_idx'),
            models.Index(fields=['responsable'], name='planes_act_responsable_idx'),
        ]

    def __str__(self):
        return f"Actividad #{self.pk} [{self.estado}]"


class Evidencia(models.Model):
    TIPOS_PERMITIDOS = ['application/pdf', 'image/jpeg', 'image/png', 'video/mp4']
    MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name='evidencias',
    )
    s3_path = models.CharField(max_length=500)
    nombre_original = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    tamaño_bytes = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.PROTECT,
        related_name='evidencias_subidas',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidencia #{self.pk} ({self.nombre_original})"
