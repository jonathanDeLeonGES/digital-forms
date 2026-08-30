# Implementation Plan

## Task Format Template

---

- [x] 1. Fundación: app Django, modelos y configuración de storage
- [x] 1.1 Crear la app `planes` con modelos PlanTrabajo, Actividad y Evidencia
  - Crear directorio `backend/apps/planes/` con estructura de archivos (models.py, services.py, serializers.py, views.py, urls.py, storage.py, tests/)
  - Definir `PlanTrabajo(TenantModel)` con `OneToOneField` a `Accion` y property `progreso`
  - Definir `Actividad(TenantModel)` con FK a PlanTrabajo, campos descripcion/responsable/fecha_limite/estado y sus choices
  - Definir `Evidencia(TenantModel)` con FK a Actividad, campos s3_path/nombre_original/content_type/tamaño_bytes/uploaded_by
  - Añadir `'apps.planes'` a `TENANT_APPS` en `config/settings/base.py`
  - Generar y aplicar migraciones; verificar creación de tablas en schema de test
  - _Requirements: 1.1, 2.1, 4.1, 6.1_

- [x] 1.2 Configurar django-storages para S3/MinIO con namespacing por tenant
  - Crear `apps/planes/storage.py` con `TenantMediaStorage` (subclase de `S3Boto3Storage`)
  - Configurar variables en `settings/dev.py` (MinIO: endpoint, access key, secret, bucket) y `settings/prod.py` (S3: región, bucket, credenciales IAM)
  - Verificar que un archivo de test se sube al bucket local de MinIO y la URL firmada es válida
  - _Requirements: 4.1, 5.1, 5.2_

---

- [x] 2. Core: servicios de plan y actividades
- [x] 2.1 (P) Implementar PlanService: CRUD de plan y actividades
  - Implementar `PlanService.create_plan(accion, actividades_data, created_by)` con validación de plan único y acción verificada
  - Implementar `PlanService.add_actividad(plan, descripcion, responsable, fecha_limite, requesting_user)` con validación de responsable del tenant
  - Implementar `PlanService.update_actividad(actividad, data, requesting_user)` con lógica diferenciada por rol
  - Implementar `PlanService.delete_actividad(actividad, requesting_user)` con guard de última actividad y limpieza de evidencias
  - `PlanTrabajo.progreso` retorna 0% sin actividades y el porcentaje correcto con actividades mixtas
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 6.1, 6.2, 6.4_
  - _Boundary: PlanService, PlanTrabajo, Actividad_

- [x] 2.2 (P) Implementar PlanService: transiciones de estado de actividades y completitud
  - Implementar `PlanService.transition_actividad(actividad, nuevo_estado, requesting_user)` con validación de rol (responsable propio vs admin/supervisor)
  - Implementar `PlanService.is_plan_complete(accion_id) -> bool` como contrato de salida para AccionService
  - Implementar `PlanService.queryset_for_user(user)` con scope por rol (admin/supervisor/verificador: todos; responsable: solo sus acciones)
  - Transición válida actualiza `actividad.estado` y el plan refleja nuevo `progreso`; transición inválida levanta `InvalidEstadoError`
  - `is_plan_complete` retorna False si no hay plan, si hay actividades no completadas; True solo si todas son completadas
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.3, 7.1, 7.2, 7.3, 7.4_
  - _Boundary: PlanService, Actividad_

- [x] 2.3 (P) Implementar FileStorageService: upload, delete y URLs firmadas
  - Implementar `FileStorageService.upload(file, tenant_slug, accion_id, actividad_id, uploaded_by, actividad)` con validación de tipo MIME (header + magic bytes) y tamaño
  - Implementar `FileStorageService.delete(evidencia)` borrando primero S3 y luego el registro DB
  - Implementar `FileStorageService.get_signed_url(evidencia, expires=3600)` usando `generate_presigned_url` de boto3
  - Upload de PDF de 1 MB a MinIO local crea registro `Evidencia` con path `{tenant_slug}/evidencias/{accion_id}/{actividad_id}/{uuid}_{nombre}`
  - URL firmada generada es accesible temporalmente y expira tras 1 hora
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_
  - _Boundary: FileStorageService, Evidencia, TenantMediaStorage_

---

- [x] 3. API: serializers, viewsets y URLs
- [x] 3.1 Implementar serializers y PlanViewSet
  - Implementar `PlanTrabajoListSerializer`, `PlanTrabajoDetailSerializer` (con `progreso` y lista de actividades) y `PlanTrabajoWriteSerializer`
  - Implementar `PlanViewSet` (GET lista, POST crear, GET detalle, PUT actualizar) usando `PlanService` y `RequireRole`
  - Registrar `/api/planes/` en `apps/planes/urls.py` e incluir en `config/urls.py`
  - `GET /api/planes/` retorna solo los planes del scope del usuario (admin ve todos, responsable ve los suyos); respuesta incluye `progreso`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.5, 7.1, 7.2, 7.3_

- [x] 3.2 Implementar ActividadViewSet con transición de estados
  - Implementar `ActividadSerializer`, `ActividadWriteSerializer`, `ActividadTransitionSerializer`
  - Implementar `ActividadViewSet` (POST crear, GET detalle, PUT editar, DELETE eliminar, POST transition) con permisos diferenciados por rol
  - `POST /api/actividades/{id}/transition/` actualiza estado y el plan refleja nuevo `progreso` en la respuesta inmediata
  - Responsable intentando editar actividad ajena → 403; campo `responsable_id` ignorado si el editor es responsable
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3_

- [x] 3.3 Implementar EvidenciaViewSet con upload multipart y signed URLs
  - Implementar `EvidenciaSerializer` (sin exponer `s3_path`)
  - Implementar `EvidenciaViewSet`: GET `/api/actividades/{id}/evidencias/`, POST upload multipart, DELETE `/api/evidencias/{id}/`, GET `/api/evidencias/{id}/signed-url/`
  - Configurar `parser_classes = [MultiPartParser]` en el endpoint de upload
  - Upload de archivo válido → 201 con `EvidenciaSerializer`; tipo inválido → 400; archivo > 50MB → 400
  - `GET /api/evidencias/{id}/signed-url/` retorna `{"url": "...", "expires_at": "..."}` con URL firmada de 1 hora
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.4, 5.5, 7.1, 7.2, 7.3, 7.4_

---

- [x] 4. Integración: contrato con acciones y frontend
- [x] 4.1 Conectar contrato is_plan_complete con AccionService
  - Verificar que `apps.acciones.services.AccionService.transition_state` llama `PlanService.is_plan_complete(accion_id)` antes de permitir "En proceso → Cerrado"
  - Si el plan no está completo, `AccionService.transition_state` retorna error 400 con mensaje descriptivo
  - Test de integración: acción con actividades incompletas no puede cerrarse; acción con todas las actividades completadas sí puede cerrarse
  - _Requirements: 6.3_
  - _Depends: 2.2_

- [x] 4.2 Implementar frontend: vista de PlanTrabajo y gestión de actividades
  - Implementar `PlanTrabajoPage.tsx` con lista de actividades, barra de progreso (`ProgressBar.tsx`) y botones de transición por rol
  - Implementar `ActividadCard.tsx` con badge de estado (`ActividadStatusBadge.tsx`) y lista de evidencias
  - Implementar `EvidenciaUploader.tsx` (dropzone para PDF/JPG/PNG/MP4, valida tamaño en cliente antes de subir)
  - Integrar `planesService.ts` con los endpoints de plan, actividad y evidencia
  - La barra de progreso se actualiza inmediatamente tras cambiar el estado de una actividad
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.5, 7.1, 7.2, 7.3_

---

- [x] 5. Validación: tests de integración, permisos y aislamiento de tenant
- [x] 5.1 Tests de integración de API y permisos por rol
  - Tests `POST /api/planes/` — admin crea plan con actividades; plan duplicado → 400; accion verificada → 400; supervisor puede crear; responsable → 403
  - Tests `POST /api/actividades/{id}/transition/` — responsable propio: éxito; responsable ajeno: 403; admin cualquier transición: éxito
  - Tests `POST /api/actividades/{id}/evidencias/` — PDF válido → 201 + archivo en MinIO; MP4 > 50MB → 400; tipo TXT → 400
  - Tests `DELETE /api/actividades/{id}/` — admin elimina actividad con evidencias: evidencias borradas de S3 y DB
  - Tests `GET /api/evidencias/{id}/signed-url/` — URL generada; verificar que URL firmada accede al archivo en MinIO de test
  - _Requirements: 1.1, 1.2, 2.1, 2.4, 3.1, 4.1, 4.2, 4.3, 4.5, 5.1, 7.1, 7.2, 7.3, 7.4_

- [x] 5.2 Tests de aislamiento de tenant y casos borde
  - Test: plan de tenant A no accesible desde tenant B (GET → 404, POST transition → 404)
  - Test: responsable no ve planes de acciones de otro responsable del mismo tenant
  - Test: `is_plan_complete` con plan inexistente → False; con actividades mixtas → False; con todas completadas → True
  - Test: eliminar última actividad del plan → 400 `LastActividadError`
  - Test: upload con content_type spoofed (PDF header pero extension .exe) → 400 (validación magic bytes)
  - _Requirements: 2.5, 5.5, 6.3, 7.5, 7.6_
