# Implementation Plan

- [ ] 1. Configuración inicial del módulo acciones
- [ ] 1.1 Crear la app Django `apps/acciones` con estructura de archivos base
  - Crear `apps/acciones/__init__.py`, `apps.py`, `models.py`, `serializers.py`, `services.py`, `signals.py`, `filters.py`, `views.py`, `urls.py` y directorio `tests/`
  - Añadir `'apps.acciones'` a `TENANT_APPS` en `backend/config/settings/base.py`
  - Crear `AccionesConfig.ready()` en `apps.py` que importa `apps.acciones.signals` para conectar handlers
  - La app aparece en `django check` sin errores y `TENANT_APPS` la incluye
  - _Requirements: 1.1_

- [ ] 2. Modelos de datos: Accion y HistorialEstado
- [ ] 2.1 Implementar el modelo `Accion` con máquina de estados
  - Definir `Accion(TenantModel)` con todos los campos: `issue` FK(PROTECT), `tipo` choices, `resultado_esperado` TextField, `responsable` FK(PROTECT), `fecha_limite` DateField, `estado` choices con default='abierto', `created_by` FK(PROTECT), `created_at`, `updated_at`
  - Definir `TIPOS`, `ESTADOS`, `TRANSICIONES_VALIDAS` y `ROLES_TRANSICION` como atributos de clase
  - Añadir índices en `estado`, `fecha_limite`, `responsable`, `issue`
  - `Accion.objects.create(...)` en schema de tenant persiste correctamente; `Accion.TRANSICIONES_VALIDAS` devuelve el grafo correcto
  - _Requirements: 1.1, 1.2, 1.3, 2.1_
  - _Boundary: Accion_

- [ ] 2.2 Implementar el modelo `HistorialEstado` y generar migraciones
  - Definir `HistorialEstado(TenantModel)` con: `accion` FK(CASCADE), `estado_anterior`, `estado_nuevo`, `usuario` FK(PROTECT), `timestamp` auto_now_add, `comentario` blank=True
  - Generar y aplicar migraciones (`makemigrations acciones`, `migrate --schema=<tenant>`)
  - Las migraciones se aplican sin errores; `HistorialEstado` creado no puede ser modificado (sin campos mutable)
  - _Requirements: 3.1, 3.3_
  - _Boundary: HistorialEstado_
  - _Depends: 2.1_

- [ ] 3. Capa de servicio: AccionService y señal de dominio
- [ ] 3.1 (P) Implementar `AccionService.create_accion` y `update_accion`
  - `create_accion`: valida que `responsable` pertenece al tenant activo; crea Accion con estado='abierto'; llama `_trigger_issue_transition_if_needed`
  - `update_accion`: verifica que el solicitante es admin; rechaza si accion.estado=='verificado'; actualiza campos editables
  - `queryset_for_user`: filtra por rol (admin/supervisor/verificador → all; responsable → solo suyas)
  - `create_accion` retorna Accion con estado='abierto'; `update_accion` rechaza acciones verificadas con ValidationError
  - _Requirements: 1.1, 1.3, 1.4, 4.1, 4.2, 6.1, 6.2, 6.3_
  - _Boundary: AccionService_

- [ ] 3.2 (P) Implementar `AccionService.transition_state` y `_validate_transition`
  - `_validate_transition`: verifica que la transición está en TRANSICIONES_VALIDAS; verifica rol (admin bypasses; responsable solo para 'abierto→en_proceso' y solo si es el asignado; supervisor para 'en_proceso→cerrado'; verificador para 'cerrado→verificado')
  - `transition_state`: llama `_validate_transition`, actualiza `accion.estado`, crea `HistorialEstado`, emite `accion_estado_cambiado`
  - Transición válida + rol correcto → Accion actualizada + HistorialEstado creado; transición inválida → InvalidTransitionError; rol incorrecto → PermissionDenied
  - _Requirements: 2.1–2.9, 3.1, 3.2_
  - _Boundary: AccionService_

- [ ] 3.3 (P) Definir y emitir la señal `accion_estado_cambiado`
  - Definir `accion_estado_cambiado = Signal()` en `signals.py` con kwargs: accion, estado_anterior, estado_nuevo, usuario, timestamp
  - Añadir el `send(...)` al final de `AccionService.transition_state` después de guardar HistorialEstado
  - La señal se emite con los kwargs correctos verificables con `django.test.utils.mock.patch` o `Signal.connect` en tests
  - _Requirements: 2.1 (señal para downstream)_
  - _Boundary: accion_estado_cambiado Signal_

- [ ] 4. API REST: serializers, filtros y viewset
- [ ] 4.1 (P) Implementar serializers
  - `AccionListSerializer`: campos de lista con `resultado_esperado_resumen` (primeros 150 chars), `responsable` como `UserBasicSerializer`, `issue` como `IssueBasicSerializer`
  - `AccionDetailSerializer`: detalle completo; incluye `historial_estados` solo para admin/supervisor (campo condicional por rol en `to_representation`)
  - `AccionWriteSerializer`: validación de FK `issue_id` e `responsable_id` en el tenant activo
  - `TransitionSerializer`: valida `estado` como choice válido; `comentario` optional
  - `HistorialEstadoSerializer`: todos los campos readonly
  - Los serializers validan campos requeridos y producen 400 con mensajes claros en campos inválidos
  - _Requirements: 1.3, 3.1, 3.4, 5.1_
  - _Boundary: AccionListSerializer, AccionDetailSerializer, AccionWriteSerializer_

- [ ] 4.2 (P) Implementar `AccionFilter`
  - Filtros por: `estado` (exact), `tipo` (exact), `responsable` (FK, exact), `fecha_limite` (range: gte/lte), `created_at` (range: gte/lte)
  - Ordenamiento por: `fecha_limite`, `created_at`, `estado`
  - `GET /api/acciones/?estado=abierto&responsable=5` retorna solo las acciones que cumplen los criterios y están en el scope del usuario
  - _Requirements: 5.2, 5.3_
  - _Boundary: AccionFilter_

- [ ] 4.3 Implementar `AccionViewSet` con todos los endpoints y acciones custom
  - CRUD estándar: `list`, `retrieve`, `create` (admin/supervisor), `update`/`partial_update` (admin), sin `destroy`
  - `@action(detail=True, methods=['POST']) transition`: llama `AccionService.transition_state`; cualquier rol autenticado puede intentar (el service valida el rol específico)
  - `@action(detail=True, methods=['GET']) historial`: retorna `HistorialEstadoSerializer` del queryset; restringido a admin/supervisor con `RequireRole`
  - Aplicar `AccionService.queryset_for_user(request.user)` en `get_queryset`
  - `POST /api/acciones/{id}/transition/` con rol incorrecto → 403; con transición inválida → 400; exitoso → 200 AccionDetailSerializer
  - _Requirements: 1.1, 1.7, 2.1–2.9, 3.4, 4.1–4.5, 5.4, 5.5, 6.1–6.3_
  - _Boundary: AccionViewSet_
  - _Depends: 3.1, 3.2, 4.1, 4.2_

- [ ] 5. Integración con issues: transición automática
- [ ] 5.1 Implementar `AccionService._trigger_issue_transition_if_needed`
  - Verificar si es la primera acción del issue: `Accion.objects.filter(issue=issue).count() == 1`
  - Verificar si `issue.estado == 'en_analisis'`
  - Si ambas condiciones, llamar `IssueService.transition_state(issue, 'acciones_generadas', usuario=created_by)`
  - Importar `IssueService` desde `apps.issues.services` (dependencia permitida explícita en boundary)
  - Crear issue en estado 'en_analisis' → crear primera acción → issue transiciona automáticamente a 'acciones_generadas'
  - _Requirements: 1.6_
  - _Boundary: AccionService, IssueService_
  - _Depends: 3.1_

- [ ] 6. Frontend: módulo de acciones
- [ ] 6.1 (P) Implementar `acciones.ts` service y `AccionListPage`
  - `acciones.ts`: funciones `listAcciones(params)`, `createAccion(data)`, `getAccion(id)`, `updateAccion(id, data)`, `transitionAccion(id, estado, comentario)`, `getHistorial(id)`
  - `AccionListPage`: tabla con filtros (estado, tipo, responsable, fechas), paginación, badges de estado con colores semánticos (abierto=gris, en_proceso=azul, cerrado=amarillo, verificado=verde)
  - La página carga el listado aplicando scope por rol (responsable ve solo sus acciones sin configuración extra — el backend filtra)
  - _Requirements: 4.2, 5.1–5.5_
  - _Boundary: acciones.ts, AccionListPage_

- [ ] 6.2 (P) Implementar `AccionDetailPage` con historial y botones de transición
  - Mostrar todos los campos de la acción, el issue vinculado (link), responsable y fecha límite
  - Mostrar historial de estados (solo para admin/supervisor; oculto para otros roles)
  - `TransitionButton`: botón que aparece solo para el rol autorizado según el estado actual; abre modal de confirmación con campo de comentario opcional
  - El botón de transición solo aparece cuando el usuario tiene el rol correcto para el estado actual de la acción
  - _Requirements: 2.1–2.9, 3.4, 4.1–4.4_
  - _Boundary: AccionDetailPage, TransitionButton_

- [ ] 6.3 (P) Implementar `AccionFormPage`
  - Formulario de creación: selector de issue (busca issues del tenant), tipo (radio/select), resultado esperado (textarea), responsable (selector de usuarios del tenant), fecha límite (date picker)
  - Formulario de edición: mismos campos; visible solo para admin; acción verificada muestra campos disabled
  - Al crear: muestra toast de éxito y redirige al detalle; errores de validación mostrados por campo
  - _Requirements: 1.1, 1.2, 1.3, 6.1, 6.2, 6.3_
  - _Boundary: AccionFormPage_

- [ ] 7. Tests y validación
- [ ] 7.1 (P) Tests unitarios del servicio y máquina de estados
  - Test `_validate_transition`: todas las combinaciones válidas e inválidas de estado y rol
  - Test `queryset_for_user`: admin ve todas, responsable solo las suyas, supervisor/verificador ven todas
  - Test `_trigger_issue_transition_if_needed`: solo actúa en primera acción + issue en 'en_analisis'
  - Test señal `accion_estado_cambiado`: kwargs correctos emitidos tras transición
  - Todos los unit tests pasan con `pytest apps/acciones/tests/test_services.py`
  - _Requirements: 2.1–2.9, 3.1, 4.1–4.5_
  - _Boundary: AccionService_

- [ ] 7.2 (P) Tests de integración de API
  - Test CRUD: crear (admin ✓, responsable 403), editar (admin ✓, verificada 400), listar (scope por rol)
  - Test transición: válida (estado actualizado + historial creado), inválida (400), rol incorrecto (403)
  - Test historial: admin/supervisor ven historial, responsable/verificador reciben 403
  - Test aislamiento de tenant: acción de tenant A → 404 desde tenant B
  - Todos los tests de integración pasan con `pytest apps/acciones/tests/test_api.py`
  - _Requirements: 1.1–1.7, 2.1–2.9, 3.1–3.5, 4.1–4.5, 5.1–5.5, 6.1–6.3_
  - _Boundary: AccionViewSet, AccionFilter_

- [ ] 7.3 Test E2E: flujo completo de acción
  - Flujo: admin crea issue → issue en 'en_analisis' → admin crea acción → issue auto-transiciona a 'acciones_generadas' → responsable mueve a 'en_proceso' → supervisor cierra → verificador verifica
  - Verificar historial de 3 entradas al final del flujo
  - El flujo completo desde creación hasta 'verificado' ejecuta sin errores y con historial completo
  - _Requirements: 1.1, 1.6, 2.1–2.9, 3.1_
  - _Depends: 7.1, 7.2_
