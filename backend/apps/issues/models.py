from django.db import models
from django_tenants.models import TenantMixin


class TenantModel(models.Model):
    """Thin alias so all issues models share the same base without importing django_tenants directly."""
    class Meta:
        abstract = True


class Issue(models.Model):
    TIPOS = [
        ('incidente', 'Incidente'),
        ('casi_incidente', 'Casi Incidente'),
        ('reunion_seguridad', 'Reunión de Seguridad'),
    ]
    GRAVEDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    ESTADOS = [
        ('abierto', 'Abierto'),
        ('en_analisis', 'En Análisis'),
        ('acciones_generadas', 'Acciones Generadas'),
        ('cerrado', 'Cerrado'),
    ]
    TRANSICIONES_VALIDAS = {
        'abierto': ['en_analisis'],
        'en_analisis': ['acciones_generadas', 'abierto'],
        'acciones_generadas': ['cerrado'],
        'cerrado': [],
    }

    tipo = models.CharField(max_length=30, choices=TIPOS)
    titulo = models.CharField(max_length=300)
    descripcion = models.TextField()
    fecha_evento = models.DateField()
    area = models.CharField(max_length=200)
    gravedad = models.CharField(max_length=20, choices=GRAVEDADES)
    estado = models.CharField(max_length=30, choices=ESTADOS, default='abierto')
    reportado_por = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.PROTECT,
        related_name='issues_reportados',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_evento']),
            models.Index(fields=['reportado_por']),
        ]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"


class DiagramaIshikawa(models.Model):
    issue = models.OneToOneField(Issue, on_delete=models.CASCADE, related_name='ishikawa')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ishikawa #{self.issue_id}"


class CausaRaiz(models.Model):
    CATEGORIAS = [
        ('metodo', 'Método'),
        ('maquina', 'Máquina'),
        ('material', 'Material'),
        ('mano_de_obra', 'Mano de Obra'),
        ('medicion', 'Medición'),
        ('medio_ambiente', 'Medio Ambiente'),
    ]
    diagrama = models.ForeignKey(DiagramaIshikawa, on_delete=models.CASCADE, related_name='causas')
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    descripcion = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_categoria_display()}: {self.descripcion[:50]}"


class SubCausa(models.Model):
    causa = models.ForeignKey(CausaRaiz, on_delete=models.CASCADE, related_name='subcausas')
    descripcion = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.descripcion[:80]


class HistorialTransicionIssue(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='historial_estados')
    estado_anterior = models.CharField(max_length=30)
    estado_nuevo = models.CharField(max_length=30)
    usuario = models.ForeignKey('users.CustomUser', on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Issue #{self.issue_id}: {self.estado_anterior} → {self.estado_nuevo}"
