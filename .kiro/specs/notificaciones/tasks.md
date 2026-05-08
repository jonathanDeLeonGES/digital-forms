# Implementation Plan

- [ ] 1. Scaffolding y configuración
- [ ] 1.1 Crear app Django `apps/notificaciones/` con estructura de archivos
  - Crear `__init__.py`, `apps.py`, `models.py`, `signals.py`, `tasks.py`, `services.py`, `serializers.py`, `views.py`, `urls.py`, `tests/`
  - Registrar `'apps.notificaciones'` en `TENANT_APPS` en `config/settings/base.py`
  - Registrar URL prefix `/api/notificaciones/` en el router principal
  - Verificable: `python manage.py check` sin errores; app aparece en `INSTALLED_APPS`
  - _Requirements: todos_
  - _Boundary: apps/notificaciones/_

- [ ] 1.2 Configurar SendGrid y variables de entorno (P)
  - Añadir `SENDGRID_API_KEY` y `DEFAULT_FROM_EMAIL` a `config/settings/base.py` (desde env vars)
  - Añadir `sendgrid` a `requirements/base.txt`
  - Verificable: `from sendgrid import SendGridAPIClient` sin error; settings exportan las variables
  - _Requirements: 1.1, 2.1, 7.1_
  - _Boundary: config/settings/base.py, requirements/base.txt_

- [ ] 1.3 Configurar Celery Beat schedules (P)
  - Registrar en `config/celery.py` las 2 tareas Beat:
    - `sgca.notificaciones.scan_deadlines_actividades` → diario 06:00 UTC
    - `sgca.notificaciones.resumen_semanal_admin` → lunes 07:00 UTC
  - Verificable: `celery inspect registered` incluye ambos task names; schedules aparecen en `CELERY_BEAT_SCHEDULE`
  - _Requirements: 2.1, 5.1_
  - _Boundary: config/celery.py_
  - _Depends: 1.1_

---

- [ ] 2. Modelos y migraciones
- [ ] 2.1 Implementar modelo ConfiguracionNotificacion
  - Definir `ConfiguracionNotificacion(TenantModel)` con `user` OneToOneField y 7 BooleanField en default=True
  - Generar y aplicar migración en schema privado
  - Verificable: `python manage.py makemigrations notificaciones && python manage.py migrate_schemas`; `ConfiguracionNotificacion.objects.get_or_create(user=user)` retorna instancia con todos los campos True
  - _Requirements: 6.1, 6.2, 6.4_
  - _Boundary: apps/notificaciones/models.py_
  - _Depends: 1.1_

- [ ] 2.2 Implementar modelo DeadlineAlertLog (P)
  - Definir `DeadlineAlertLog(TenantModel)` con `actividad_id` IntegerField (FK lógica), `tipo_alerta` CharField choices, `fecha_envio` DateField, `unique_together`
  - Generar y aplicar migración
  - Verificable: `DeadlineAlertLog.objects.get_or_create(actividad_id=1, tipo_alerta='3d', fecha_envio=today)` crea una vez; segunda llamada retorna `created=False`
  - _Requirements: 2.7, 7.5_
  - _Boundary: apps/notificaciones/models.py_
  - _Depends: 1.1_

---

- [ ] 3. NotificacionService
- [ ] 3.1 Implementar NotificacionService
  - Métodos: `send_to_user(user, tipo, context, subject)`, `send_to_role(role, tipo, context, subject)`, `get_config(user)`, `should_send(user, tipo)`, `_render_email(template_name, context)`, `_send_via_sendgrid(to_email, subject, html_content)`
  - `should_send` retorna False si `user.is_active=False` o si la preferencia del tipo está desactivada
  - `_send_via_sendgrid` lanza excepción en error HTTP para que Celery haga retry
  - Verificable: tests unitarios de `should_send` con user inactivo → False; preferencia desactivada → False; user activo con preferencia → True
  - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - _Boundary: apps/notificaciones/services.py_
  - _Depends: 2.1_

---

- [ ] 4. Templates HTML de email
- [ ] 4.1 Crear 7 plantillas HTML de email
  - `asignacion_accion.html` — email al responsable con datos de la acción asignada
  - `deadline_3d.html` — alerta de actividad con deadline en 3 días
  - `deadline_1d.html` — alerta de actividad con deadline mañana
  - `deadline_vencido.html` — alerta de actividad con deadline vencido
  - `accion_lista_revision.html` — email a supervisores con datos de la acción lista para revisar
  - `verificacion_proxima.html` — email a verificadores con datos de la verificación próxima
  - `resumen_semanal.html` — resumen semanal de métricas al admin
  - Verificable: `render_to_string('notificaciones/asignacion_accion.html', ctx)` retorna HTML con los datos del contexto; todos los templates renderizan sin error con contexto mínimo
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_
  - _Boundary: apps/notificaciones/templates/notificaciones/_
  - _Depends: 1.1_

---

- [ ] 5. Signal handlers
- [ ] 5.1 Implementar handle_accion_estado_cambiado
  - Conectar `@receiver(accion_estado_cambiado)` en `signals.py`
  - Si `estado_nuevo == 'en_proceso'` → `.delay(accion.id)` a `enviar_email_asignacion_accion`
  - Si `estado_nuevo == 'cerrado'` → `.delay(accion.id)` a `enviar_email_accion_lista_revision`
  - Capturar toda excepción con log ERROR sin re-lanzar
  - Registrar handler en `NotificacionesConfig.ready()` (apps.py)
  - Verificable: test de señal con `accion_estado_cambiado.send(...)` → tarea Celery encolada (con `task_always_eager=True`); excepción en tarea → no propaga al emisor
  - _Requirements: 1.1, 1.2, 3.1, 7.3_
  - _Boundary: apps/notificaciones/signals.py, apps/notificaciones/apps.py_
  - _Depends: 3.1_

- [ ] 5.2 Implementar handle_verificacion_proxima (P)
  - Conectar `@receiver(verificacion_proxima_detectada)` en `signals.py`
  - `.delay(verificacion.id, tenant.schema_name)` a `enviar_email_verificacion_proxima`
  - Capturar toda excepción con log ERROR sin re-lanzar
  - Verificable: test con `verificacion_proxima_detectada.send(...)` → tarea Celery encolada; excepción → capturada sin propagación
  - _Requirements: 4.1, 7.3_
  - _Boundary: apps/notificaciones/signals.py_
  - _Depends: 3.1_

---

- [ ] 6. Celery tasks async
- [ ] 6.1 Implementar enviar_email_asignacion_accion
  - `@shared_task(name='sgca.notificaciones.enviar_email_asignacion_accion', max_retries=3, retry_backoff=True)`
  - Obtener Accion por ID → NotificacionService.send_to_user(accion.responsable, 'asignacion_accion', ctx, subject)
  - Verificable: `enviar_email_asignacion_accion.apply(args=[accion_id])` con SendGrid mock → service.send_to_user llamado; responsable desactivado → no llamado
  - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - _Boundary: apps/notificaciones/tasks.py_
  - _Depends: 3.1, 4.1_

- [ ] 6.2 Implementar enviar_email_accion_lista_revision (P)
  - `@shared_task(name='sgca.notificaciones.enviar_email_accion_lista_revision', max_retries=3, retry_backoff=True)`
  - Obtener Accion → NotificacionService.send_to_role('supervisor', 'accion_revision', ctx, subject)
  - Verificable: con supervisores activos → emails enviados; sin supervisores activos → skip sin error
  - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - _Boundary: apps/notificaciones/tasks.py_
  - _Depends: 3.1, 4.1_

- [ ] 6.3 Implementar enviar_email_verificacion_proxima (P)
  - `@shared_task(name='sgca.notificaciones.enviar_email_verificacion_proxima', max_retries=3, retry_backoff=True)`
  - `schema_context(tenant_schema)` → VerificacionEficacia.objects.get(id) → send_to_role('verificador', ...)
  - Verificable: verificadores activos → emails enviados; verificadores desactivados → skip
  - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - _Boundary: apps/notificaciones/tasks.py_
  - _Depends: 3.1, 4.1_

---

- [ ] 7. Celery Beat tasks
- [ ] 7.1 Implementar scan_deadlines_actividades
  - `@shared_task(name='sgca.notificaciones.scan_deadlines_actividades')`
  - Iterar tenants activos con `schema_context`
  - Por tenant: query `Actividad.objects.filter(fecha_limite__lte=hoy+3d, estado__in=['pendiente','en_proceso'])`
  - Por actividad y tipo ('3d', '1d', 'vencido'): `DeadlineAlertLog.objects.get_or_create(...)` → si creado → NotificacionService.send_to_user
  - Verificable: actividad vencida pendiente → email + log creado; segunda ejecución mismo día → no email (idempotente); actividad completada → ignorada
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_
  - _Boundary: apps/notificaciones/tasks.py_
  - _Depends: 3.1, 2.2_

- [ ] 7.2 Implementar resumen_semanal_admin (P)
  - `@shared_task(name='sgca.notificaciones.resumen_semanal_admin')`
  - Iterar tenants activos → agregar métricas (acciones por estado, actividades vencidas, issues del mes)
  - NotificacionService.send_to_role('admin', 'resumen_semanal', ctx, subject)
  - Verificable: tenant con admin activo → email enviado; tenant sin admins → skip sin error; métricas en el contexto son correctas
  - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - _Boundary: apps/notificaciones/tasks.py_
  - _Depends: 3.1_

---

- [ ] 8. API de preferencias
- [ ] 8.1 Implementar PreferenciasNotificacionView y serializer
  - `ConfiguracionNotificacionSerializer` con los 7 campos booleanos + `updated_at` (readonly)
  - `PreferenciasNotificacionView(RetrieveUpdateAPIView)` con GET y PATCH
  - `get_object()` usa `get_or_create` para retornar o crear config con defaults
  - Proteger con `IsAuthenticated` (cualquier rol autenticado puede ver y editar sus propias preferencias)
  - Registrar en `urls.py`: `GET|PATCH /api/notificaciones/preferencias/`
  - Verificable: `GET /api/notificaciones/preferencias/` → 200 con todos True para usuario nuevo; `PATCH` con `notif_deadline_3d: false` → 200 con valor actualizado; sin token → 401; campo inválido → 400
  - _Requirements: 6.1, 6.3, 6.4_
  - _Boundary: apps/notificaciones/views.py, apps/notificaciones/serializers.py, apps/notificaciones/urls.py_
  - _Depends: 2.1_

---

- [ ] 9. Tests de integración y E2E
- [ ] 9.1 Tests de integración de signal handlers y tareas
  - `test_signals.py`: handle_accion_estado_cambiado con estado 'en_proceso' → task encolada; con 'cerrado' → task encolada; con 'abierto' → no encolada; excepción → capturada
  - `test_tasks.py` (con SendGrid mock): enviar_email_asignacion_accion con responsable activo → send llamado; responsable desactivado → no llamado; SendGrid falla → Celery retry
  - `test_tasks.py` scan_deadlines_actividades: actividad vencida → email + log; segunda ejecución → no duplicado; actividad completada → ignorada
  - Verificable: `pytest apps/notificaciones/tests/ -v` → todos los tests pasan; aislamiento por tenant verificado
  - _Requirements: 1–7_
  - _Boundary: apps/notificaciones/tests/_
  - _Depends: 5.1, 5.2, 6.1, 6.2, 6.3, 7.1, 7.2_

- [ ] 9.2 Test E2E: flujo completo de notificación (P)
  - AccionService transiciona acción a 'en_proceso' → señal emitida → handler despacha tarea → email enviado al responsable (SendGrid mock)
  - scan_deadlines_actividades con actividades vencidas → emails + logs creados; segunda ejecución → idempotente
  - Usuario desactiva preferencia `notif_deadline_3d` → scan → no envía alerta 3d a ese usuario pero sí a otros
  - Verificable: flujos E2E pasan; `pytest apps/notificaciones/tests/test_e2e.py -v`
  - _Requirements: 1.1, 2.1, 6.2_
  - _Boundary: apps/notificaciones/tests/test_e2e.py_
  - _Depends: 9.1_
