# Research: notificaciones

## Discovery Scope
Feature type: Complex Integration (escucha múltiples señales upstream, tareas Celery Beat multi-tenant, SendGrid API, idempotencia de alertas).

## Key Findings

### 1. Upstream Signal Contracts
- `accion_estado_cambiado` (apps/acciones/signals.py): kwargs = {accion, estado_anterior, estado_nuevo, usuario, timestamp}
- `verificacion_proxima_detectada` (apps/verificacion/signals.py): kwargs = {verificacion, accion, tenant}
- Handlers deben capturar sus propias excepciones — ninguna señal revierte la transacción upstream si el handler falla.

### 2. Actividad.fecha_limite — Fuente para Deadline Scanning
- Modelo en apps/planes/models.py
- Campo: DateField
- Índice en (fecha_limite, estado) según diseño de planes-trabajo
- La tarea de deadline scanning lee directamente el modelo — no hay contrato de servicio intermedio.

### 3. Celery Beat — Coordinación de Nombres
- Nombre reservado por verificacion-eficacia: `sgca.verificacion.detectar_verificaciones_proximas`
- Nombres elegidos para notificaciones: `sgca.notificaciones.scan_deadlines_actividades` (diario) y `sgca.notificaciones.resumen_semanal_admin` (semanal)
- Ambas tareas son multi-tenant: iteran sobre tenants activos con schema_context.

### 4. Idempotencia de Alertas de Deadline
- Estrategia: tabla DeadlineAlertLog con unique_together (actividad_id, tipo_alerta, fecha_envio)
- Antes de enviar, se verifica si existe el registro; si no existe, se crea atómicamente (get_or_create) y se envía.
- Esto garantiza exactamente-una-vez por día calendario por actividad y tipo.

### 5. SendGrid Integration
- SDK oficial: sendgrid-python
- Método: sg.send(mail) con Mail object
- Reintentos: max_retries=3 con autoretry_for=(Exception,) y exponential backoff en la tarea Celery.
- No usar SendGrid Dynamic Templates para evitar dependencia de IDs externos; usar plantillas HTML locales Django.

### 6. ConfiguracionNotificacion — Diseño de Modelo
- Relación: OneToOneField con CustomUser (un registro por usuario)
- 7 campos BooleanField (uno por tipo de notificación), todos default=True
- Al consultar preferencias: get_or_create para garantizar defaults sin migración de datos.

## Architecture Decisions

### Decision 1: Handlers síncronos → dispatch a Celery async
Los handlers de señal son síncronos (dentro de la transacción upstream). Para no bloquear, los handlers solo extraen IDs y hacen `.delay()` a tareas Celery. Nunca cargan objetos completos ni hacen queries en el handler.

### Decision 2: DeadlineAlertLog para idempotencia
Alternativa considerada: idempotency key en Celery. Rechazada porque Celery idempotency keys tienen TTL y no garantizan persistencia. La tabla DB garantiza idempotencia duradera y auditable.

### Decision 3: HTML templates locales (no SendGrid Dynamic Templates)
Usar templates Django (apps/notificaciones/templates/) evita dependencia de IDs de templates en SendGrid y permite versionar las templates junto al código.
