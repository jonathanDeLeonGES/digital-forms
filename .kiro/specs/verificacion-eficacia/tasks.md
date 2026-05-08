# Implementation Plan

- [ ] 1. Foundation: modelo y configuración de la app verificacion
- [ ] 1.1 Crear modelo VerificacionEficacia y migración inicial
  - Definir modelo con campos: accion (FK CASCADE), fecha_programada, fecha_real (null), resultado (choices), verificador (FK null), notas, issue_resultado (FK SET_NULL null)
  - Configurar unique_together ('accion', 'fecha_programada') para deduplicación
  - Agregar índice compuesto (fecha_programada, resultado) para lookup diario
  - La migración ejecuta sin errores y el modelo aparece en el schema del tenant activo
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1_
  - _Boundary: VerificacionEficacia_

- [ ] 1.2 Configurar app apps/verificacion/ y registrarla en Django
  - Crear `apps/verificacion/apps.py` con VerificacionConfig que conecta señales en `ready()`
  - Añadir 'apps.verificacion' a TENANT_APPS en settings/base.py
  - `python manage.py check` ejecuta sin errores con la nueva app registrada
  - _Requirements: 1.1, 2.2_

- [ ] 2. Core: handler de señal, servicio y tarea Celery Beat
- [ ] 2.1 (P) Implementar ProgramarVerificacionesHandler y VerificacionService.programar_verificaciones
  - Definir señal `verificacion_proxima_detectada` en apps/verificacion/signals.py con kwargs: verificacion, accion, tenant
  - Implementar handler `@receiver(accion_estado_cambiado)` que actúa solo cuando estado_nuevo=='cerrado'
  - Implementar `VerificacionService.programar_verificaciones(accion, fecha_cierre)`: bulk_create 3 registros (+6m, +12m, +24m) con ignore_conflicts=True
  - Test: al emitir accion_estado_cambiado con estado_nuevo='cerrado', se crean exactamente 3 verificaciones en el schema del tenant
  - Test: emitir la señal dos veces (re-cierre) no duplica registros
  - _Requirements: 1.1, 1.2, 1.3, 1.5_
  - _Boundary: ProgramarVerificacionesHandler, VerificacionService_

- [ ] 2.2 (P) Implementar VerificacionService.registrar_resultado y crear_issue_reincidencia
  - Implementar `registrar_resultado(verificacion, resultado, notas, verificador)`: actualiza resultado, fecha_real, verificador, notas; lanza ValidationError si resultado != 'pendiente' (ya completada)
  - Implementar `crear_issue_reincidencia(verificacion, solicitado_por)`: crea Issue tipo='incidente', estado='abierto'; vincula verificacion.issue_resultado; lanza error si resultado != 'no_eficaz' o si issue ya existe
  - Implementar `get_verificaciones_hoy()`: filtra por fecha_programada==today y resultado=='pendiente'
  - Test: registrar_resultado actualiza campos correctamente; segunda llamada lanza ValidationError
  - Test: crear_issue_reincidencia crea Issue en el tenant activo y vincula verificacion.issue_resultado
  - _Requirements: 2.1, 3.1, 3.2, 3.5, 4.1, 4.2, 4.3, 4.4_
  - _Boundary: VerificacionService_

- [ ] 2.3 (P) Implementar tarea Celery Beat detectar_verificaciones_proximas
  - Implementar `@shared_task(name='sgca.verificacion.detectar_verificaciones_proximas')` en tasks.py
  - Iterar sobre tenants activos con schema_context; para cada tenant llamar get_verificaciones_hoy() y emitir verificacion_proxima_detectada
  - Registrar schedule diario (01:00 UTC) en config/celery.py
  - Test: tarea detecta verificaciones con fecha==hoy y emite señal por cada una; no emite para resultado != 'pendiente'
  - Test: ejecutada dos veces el mismo día no emite señales duplicadas (idempotencia por filtro resultado=='pendiente')
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 6.2_
  - _Boundary: detectar_verificaciones_proximas_

- [ ] 3. API: endpoints de listado y registro
- [ ] 3.1 Implementar endpoint de listado de verificaciones por acción
  - Crear VerificacionSerializer con campos: id, accion_id, fecha_programada, fecha_real, resultado, verificador (UserBasicSerializer|None), notas, issue_resultado_id, created_at
  - Crear endpoint GET /api/acciones/{accion_id}/verificaciones/ accesible solo a roles admin y supervisor (RequireRole)
  - Ordenar resultados por fecha_programada ascendente
  - Test: admin ve lista ordenada; supervisor ve lista; responsable recibe 403; verificador recibe 403
  - Test: 404 si accion_id no pertenece al tenant activo
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.3_
  - _Boundary: VerificacionViewSet_

- [ ] 3.2 Implementar endpoint de registro de resultado
  - Crear RegistrarResultadoSerializer: resultado (required, choices=[eficaz, no_eficaz]), notas (optional)
  - Crear endpoint POST /api/verificaciones/{id}/registrar/ con RequireRole(verificador)
  - Invocar VerificacionService.registrar_resultado; mapear ValidationError a 400
  - Test: verificador registra 'eficaz' → 200 con datos actualizados; admin → 403; responsable → 403
  - Test: segundo intento de registro → 400 con mensaje "ya fue completada"
  - Test: campo resultado ausente → 400 con error de campo
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - _Boundary: VerificacionViewSet_

- [ ] 3.3 Implementar endpoint de creación de issue de reincidencia
  - Crear endpoint POST /api/verificaciones/{id}/crear-issue/ con RequireRole(verificador)
  - Invocar VerificacionService.crear_issue_reincidencia; retornar {issue_id: N} con 201
  - Mapear ValidationError a 400 para casos: resultado != no_eficaz, issue ya existe
  - Test: verificador con resultado no_eficaz crea issue → 201 con issue_id; issue existe en tenant activo con estado abierto
  - Test: resultado eficaz → 400; issue ya creado → 400
  - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - _Boundary: VerificacionViewSet_
  - _Depends: 3.2_

- [ ] 4. Frontend: componentes React
- [ ] 4.1 (P) Implementar VerificacionListPage y VerificacionCard
  - Crear VerificacionCard: muestra fecha_programada, resultado (badge coloreado), verificador, notas
  - Crear VerificacionListPage: lista de verificaciones de una acción consultando GET /api/acciones/{id}/verificaciones/
  - Visible solo para admin y supervisor (ocultar en frontend para otros roles)
  - La página renderiza la lista ordenada con estado visual claro (pendiente/eficaz/no_eficaz)
  - _Requirements: 5.1, 5.2, 5.3_
  - _Boundary: VerificacionListPage, VerificacionCard_

- [ ] 4.2 (P) Implementar RegistrarResultadoForm
  - Crear formulario para verificador: campo resultado (select: eficaz/no_eficaz) + notas (textarea opcional)
  - Mostrar opción "Crear issue de reincidencia" solo cuando resultado seleccionado es no_eficaz
  - Al enviar, llamar POST /api/verificaciones/{id}/registrar/ y si se solicita issue llamar POST /api/verificaciones/{id}/crear-issue/
  - El formulario muestra confirmación de registro y deshabilita re-envío tras éxito
  - _Requirements: 3.1, 3.2, 4.1, 4.3_
  - _Boundary: RegistrarResultadoForm_

- [ ] 5. Integración y tests de aislamiento
- [ ] 5.1 Tests de integración del handler de señal y flujo completo de cierre
  - Verificar que cerrar una Accion (vía AccionService.transition_state) crea automáticamente 3 VerificacionEficacia en el schema del tenant
  - Verificar deduplicación: cerrar la misma Accion dos veces no duplica registros
  - Verificar que estados distintos a 'cerrado' no crean verificaciones
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [ ] 5.2 Tests de aislamiento de tenant
  - Verificar que verificaciones de tenant A no son accesibles desde tenant B (404 en GET y POST)
  - Verificar que la tarea Celery Beat no mezcla datos entre tenants al iterar
  - Verificar que Issue de reincidencia se crea en el tenant del verificador (mismo schema)
  - _Requirements: 6.1, 6.2, 6.3_

- [ ]* 5.3 Tests opcionales: E2E flujo completo
  - Flujo completo: issue → acción → cierre → 3 verificaciones → registro resultado 'no_eficaz' → issue de reincidencia → admin ve historial completo con 3 registros
  - Verificar que segunda verificación (+12m) sigue en estado 'pendiente' después de registrar la primera (+6m)
  - _Requirements: 1.1, 3.1, 4.1, 5.1, 5.2_
