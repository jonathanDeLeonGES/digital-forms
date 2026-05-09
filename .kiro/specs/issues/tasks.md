# Implementation Plan

- [x] 1. Fundación: app Django y modelos de datos
- [x] 1.1 Crear la app Django `issues` con sus modelos
  - Crear directorio `backend/apps/issues/` con `__init__.py`, `apps.py`
  - Definir `Issue` (TenantModel) con campos: tipo, titulo, descripcion, fecha_evento, area, gravedad, estado, reportado_por (FK CustomUser), created_at, updated_at
  - Definir `DiagramaIshikawa` (TenantModel) con OneToOneField a Issue (CASCADE)
  - Definir `CausaRaiz` (TenantModel) con FK a DiagramaIshikawa, campo categoria (6 choices fijos), descripcion
  - Definir `SubCausa` (TenantModel) con FK a CausaRaiz (CASCADE), descripcion
  - Definir `HistorialTransicionIssue` (TenantModel) con FK a Issue (CASCADE), FK a CustomUser (PROTECT), estado_anterior, estado_nuevo, timestamp (auto_now_add), comentario
  - Observable: `python manage.py makemigrations issues` genera migración sin errores; todos los modelos heredan de TenantModel
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 3.5, 6.1_

- [x] 1.2 Migrar y registrar la app en settings
  - Añadir `'apps.issues'` a TENANT_APPS en `backend/config/settings/base.py`
  - Ejecutar `migrate_schemas --shared` para aplicar migración al schema público (no aplica, solo tenant) — ejecutar `migrate_schemas` para schemas de tenant
  - Observable: La migración se aplica sin errores; las tablas `issues_issue`, `issues_diagramaishikawa`, `issues_causaraiz`, `issues_subcausa`, `issues_historialtransicionissue` existen en el schema del tenant de prueba
  - _Requirements: 6.1, 6.2_

- [x] 2. Lógica de negocio: IssueService
- [x] 2.1 Implementar IssueService — CRUD y visibilidad por rol
  - Implementar `create_issue(tipo, titulo, descripcion, fecha_evento, area, gravedad, reportado_por) -> Issue`
  - Implementar `update_issue(issue, data, requesting_user) -> Issue` con verificación de permisos por rol
  - Implementar `queryset_for_user(user) -> QuerySet[Issue]`: admin/supervisor → todos; responsable → solo propios; verificador → todos (read-only enforcement en la vista)
  - Observable: Tests unitarios para `queryset_for_user` pasan: admin ve N issues, responsable ve solo los suyos, verificador ve todos
  - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3, 6.2, 6.3_
  - _Boundary: IssueService_

- [x] 2.2 Implementar IssueService — transiciones de estado
  - Implementar `transition_state(issue, nuevo_estado, requesting_user, comentario='') -> Issue`
  - Validar contra `Issue.TRANSICIONES_VALIDAS`; lanzar `InvalidTransitionError` si no es válida
  - Verificar que solo admin/supervisor pueden realizar transiciones a/desde estados avanzados
  - Crear `HistorialTransicionIssue` en cada transición exitosa
  - Observable: `IssueService.transition_state(issue, 'en_analisis', user)` actualiza `issue.estado` y crea un `HistorialTransicionIssue` en la DB; intentar transición inválida lanza `InvalidTransitionError`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - _Boundary: IssueService_

- [x] 2.3 Implementar IssueService — upsert Ishikawa
  - Implementar `upsert_ishikawa(issue, causas_por_categoria) -> DiagramaIshikawa`
  - Crear `DiagramaIshikawa` si no existe
  - Hacer upsert de CausaRaiz por categoría: crear las nuevas, actualizar las existentes, eliminar las removidas del payload de su categoría
  - Hacer upsert de SubCausa por causa con el mismo patrón
  - Observable: Llamar `upsert_ishikawa` con {metodo: [{descripcion: "X", subcausas: [{descripcion: "Y"}]}]} crea DiagramaIshikawa + CausaRaiz + SubCausa en DB; una segunda llamada sin la categoría "metodo" la preserva intacta
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  - _Boundary: IssueService_

- [x] 3. API REST: serializers, filtros y ViewSets
- [x] 3.1 (P) Implementar serializers y filtros
  - Implementar `IssueListSerializer` (campos de listado sin descripción ni ishikawa)
  - Implementar `IssueDetailSerializer` (incluye ishikawa anidado y historial para admin/supervisor)
  - Implementar `IssueWriteSerializer` con validación de choices
  - Implementar `IshikawaSerializer`, `CausaRaizSerializer`, `SubCausaSerializer`
  - Implementar `IssueFilter` (django-filter) para: tipo, estado, gravedad, area (exact), fecha_evento__gte, fecha_evento__lte
  - Observable: `IssueFilter(data={'estado': 'abierto'}, queryset=Issue.objects.all()).qs` retorna solo issues en estado abierto
  - _Requirements: 1.5, 2.1, 5.1, 5.2, 5.3, 5.4, 5.5_
  - _Boundary: serializers.py, filters.py_

- [x] 3.2 (P) Implementar IssueViewSet
  - Crear `IssueViewSet` (ModelViewSet) usando `IssueService.queryset_for_user(request.user)` como base queryset
  - Aplicar `permission_classes`: `IsAuthenticated` + `RequireRole` según acción (create: todos; update/delete: admin/supervisor/responsable propio)
  - Implementar acción custom `transition` (POST `/{id}/transition/`)
  - Conectar `IssueFilter` como `filterset_class`
  - Implementar paginación estándar DRF con `page` y `page_size`
  - Observable: `GET /api/issues/` como responsable retorna solo sus issues con paginación; `POST /api/issues/{id}/transition/` con estado válido retorna 200 con issue actualizado
  - _Requirements: 1.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 5.1, 5.6_
  - _Boundary: IssueViewSet_

- [x] 3.3 (P) Implementar IshikawaView y URLs
  - Crear `IshikawaView` (APIView): GET retorna 404 si no existe; PUT llama `IssueService.upsert_ishikawa()`
  - Crear `backend/apps/issues/urls.py` con routes para IssueViewSet e IshikawaView
  - Registrar en `backend/config/urls_tenant.py`
  - Observable: `GET /api/issues/{id}/ishikawa/` en un issue sin Ishikawa retorna 404; `PUT` con payload válido retorna 200 con las 6 categorías en la respuesta
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  - _Boundary: IshikawaView, urls.py_

- [x] 4. Frontend
- [x] 4.1 (P) Implementar issuesService y página de listado
  - Implementar `frontend/src/services/issues.ts` con: `getIssues(filters)`, `createIssue(data)`, `getIssue(id)`, `updateIssue(id, data)`, `transitionIssue(id, estado)`, `getIshikawa(id)`, `updateIshikawa(id, data)`
  - Implementar `IssueListPage.tsx` con tabla/lista paginada, controles de filtro (tipo, estado, gravedad, área, rango de fecha), badge de estado coloreado (`IssueStatusBadge.tsx`)
  - Observable: La página muestra los issues del tenant con filtros aplicables; el badge de estado muestra el color correcto según el estado
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - _Boundary: IssueListPage, issuesService_

- [x] 4.2 (P) Implementar formulario de creación/edición e Ishikawa
  - Implementar `IssueFormPage.tsx` con campos de Issue y sección separada de Ishikawa
  - Implementar `IshikawaForm.tsx` con 6 acordeones (uno por categoría), botón "Agregar causa" por categoría, y "Agregar subcausa" por causa
  - Observable: El formulario de creación envía `POST /api/issues/` y redirige al detalle; el componente Ishikawa permite agregar causas y subcausas a cualquiera de las 6 categorías
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4_
  - _Boundary: IssueFormPage, IshikawaForm_

- [x] 4.3 (P) Implementar página de detalle del Issue
  - Implementar `IssueDetailPage.tsx` mostrando datos del issue, Ishikawa (si existe), historial de estados (para admin/supervisor) y botones de transición de estado según rol
  - Observable: La página detalle carga el issue, muestra el Ishikawa anidado con causas/subcausas, y los botones de transición solo aparecen para roles autorizados
  - _Requirements: 3.1, 3.2, 3.3, 3.6, 4.1, 4.2, 4.3_
  - _Boundary: IssueDetailPage_

- [x] 5. Tests de backend
- [x] 5.1 (P) Tests de modelos y servicio
  - Test: `Issue.TRANSICIONES_VALIDAS` cubre todos los estados; transiciones inválidas detectadas
  - Test: `IssueService.queryset_for_user()` — admin ve todos, responsable ve solo los suyos
  - Test: `IssueService.upsert_ishikawa()` — preserva categorías no enviadas; cascade delete de SubCausa al eliminar CausaRaiz
  - Test: `IssueService.transition_state()` — exitosa crea HistorialTransicionIssue; inválida lanza `InvalidTransitionError`
  - Observable: `pytest apps/issues/tests/test_models.py` pasa sin errores
  - _Requirements: 1.3, 2.4, 2.5, 2.6, 3.1, 3.4, 3.5_
  - _Boundary: IssueService, modelos_

- [x] 5.2 (P) Tests de API — endpoints y permisos
  - Test: `POST /api/issues/` con todos los campos → 201; campo faltante → 400
  - Test: `GET /api/issues/` con filtros por tipo, estado, área, gravedad → retorna solo matching
  - Test: Responsable solo ve sus issues; verificador ve todos en read-only (PUT → 403)
  - Test: `POST /api/issues/{id}/transition/` transición válida → 200 + historial creado; inválida → 400
  - Test: Aislamiento de tenant — issue de tenant A retorna 404 desde tenant B con mismo id
  - Observable: `pytest apps/issues/tests/test_api.py` y `test_permissions.py` pasan sin errores
  - _Requirements: 1.1, 1.2, 3.2, 3.4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.6, 6.2, 6.3_
  - _Boundary: IssueViewSet, IshikawaView_

- [x] 5.3 (P) Tests E2E del flujo completo
  - E2E: Usuario crea issue → admin transiciona estados hasta "Cerrado" → historial completo visible
  - E2E: Responsable crea issue → no ve issues de otro responsable en la lista
  - E2E: PUT Ishikawa con 3 categorías → GET muestra las 6 con 3 vacías y 3 con causas
  - Observable: Todos los flujos E2E pasan sin errores de integración entre frontend y backend
  - _Requirements: 1.1, 2.1, 3.1, 4.2, 5.1_
  - _Boundary: IssueViewSet, IshikawaView, IssueListPage_
