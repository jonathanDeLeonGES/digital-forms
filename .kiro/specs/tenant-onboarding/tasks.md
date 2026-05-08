# Implementation Plan — tenant-onboarding

- [ ] 1. Configuración de django-tenants en el proyecto
- [x] 1.1 Configurar settings para schema-per-tenant
  - Agregar `django-tenants` a INSTALLED_APPS y configurar `SHARED_APPS` y `TENANT_APPS` según la separación de modelos (tenants app en SHARED_APPS; apps de negocio vacías por ahora en TENANT_APPS)
  - Configurar `DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']`
  - Agregar `TenantMiddleware` como primer middleware en la lista `MIDDLEWARE`
  - Configurar `TENANT_MODEL = 'tenants.Tenant'` y `TENANT_DOMAIN_MODEL = 'tenants.Domain'`
  - La configuración de settings permite ejecutar `python manage.py migrate_schemas --shared` sin errores
  - _Requirements: 2.1, 4.1_

- [ ] 1.2 Configurar URL routing público y de tenant
  - Crear `config/urls_public.py` con las rutas del schema público: endpoint de registro (`/api/public/`) y Django Admin (`/admin/`)
  - Crear `config/urls_tenant.py` con rutas vacías (placeholder para Wave 2+)
  - Configurar `ROOT_URLCONF` y `PUBLIC_SCHEMA_URLCONF` en settings
  - El servidor Django arranca sin errores y el Admin es accesible en el dominio público
  - _Requirements: 4.1, 6.3_

- [ ] 2. Modelos del schema público
- [ ] 2.1 Implementar modelos Tenant y Domain
  - Crear modelo `Tenant` heredando de `TenantMixin` con campos `nombre_empresa` (str, max 200), `email_admin` (EmailField), `created_at`; establecer `auto_create_schema = True` y `auto_drop_schema = True`
  - Crear modelo `Domain` heredando de `DomainMixin`
  - El validador de subdominio `validate_subdomain_format()` rechaza subdominios con caracteres inválidos (solo `[a-z0-9][a-z0-9-]*[a-z0-9]`)
  - `Tenant.save()` crea automáticamente el schema PostgreSQL del tenant al persistirse
  - _Requirements: 1.1, 1.3, 2.1, 2.2, 4.1_

- [ ] 2.2 Implementar modelos Plan y Subscription
  - Crear modelo `Plan` con campo `nombre` choices (`trial`, `enterprise`), datos fijos cargados via fixture
  - Crear modelo `Subscription` con FKs a `Tenant` (OneToOne) y `Plan`, campos `fecha_inicio`, `fecha_fin` (null para Enterprise), `num_licencias` (null para Trial)
  - Implementar `Subscription.is_active()`: retorna `True` si plan es Enterprise o si `fecha_fin >= date.today()`
  - Tests unitarios de `is_active()` cubren: trial activo, trial vencido hoy, trial vencido ayer, Enterprise sin fecha_fin
  - _Requirements: 3.1, 5.4_

- [ ] 2.3 Crear migraciones y fixture inicial de planes
  - Generar y aplicar migraciones del schema público para los 4 modelos
  - Crear fixture `tenants/fixtures/initial_plans.json` con los dos registros: `trial` y `enterprise`
  - `python manage.py migrate_schemas --shared` completa sin errores y `Plan.objects.count() == 2` tras cargar el fixture
  - _Requirements: 3.1_

- [ ] 3. Servicio y API de registro de tenant (P)
  - _Boundary: TenantRegistrationService, TenantRegistrationView, TenantRegistrationSerializer_

- [ ] 3.1 Implementar TenantRegistrationService
  - Implementar `TenantRegistrationService.register(nombre_empresa, subdominio, email_admin)` que orquesta: crear `Tenant` (auto-schema), crear `Domain`, crear `Subscription` (plan=trial, fecha_fin=hoy+14 días)
  - Manejar `IntegrityError` en la creación de `Domain` (subdominio duplicado) → lanzar `SubdomainAlreadyExistsError` y llamar `tenant.delete()` para cleanup
  - Si cualquier paso posterior falla, llamar `tenant.delete()` antes de re-lanzar la excepción
  - Test de integración: verificar que un fallo en la creación de `Subscription` no deja registros huérfanos
  - _Requirements: 1.1, 1.2, 1.4, 2.3_

- [ ] 3.2 Implementar serializer, view y URL de registro
  - Crear `TenantRegistrationSerializer` con campos `nombre_empresa`, `subdominio` (con validación de formato), `email_admin`
  - Crear `TenantRegistrationView` (APIView, sin autenticación) que delega a `TenantRegistrationService` y retorna 201 con `{id, subdominio, trial_expires_at, message}` en éxito; 409 para subdominio duplicado; 400 para errores de validación
  - Registrar `POST /api/public/tenants/register/` en `urls_public.py`
  - `curl -X POST /api/public/tenants/register/ -d '{"nombre_empresa":"ACME","subdominio":"acme","email_admin":"a@b.com"}'` retorna HTTP 201 con el body esperado
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [ ] 4. (P) AccessPolicyMiddleware
  - _Boundary: AccessPolicyMiddleware_
  - Implementar `AccessPolicyMiddleware` que: verifica si `request.tenant` está presente (si no, es schema público → pasar); comprueba si la ruta está en la whitelist (`/admin/`, `/api/public/`, `/static/`, `/media/`) → pasar; llama `request.tenant.subscription.is_active()` → si `False`, retorna JSON `{"detail": "...", "code": "trial_expired"}` con status 402
  - Registrar el middleware en `MIDDLEWARE` después de `TenantMiddleware`
  - Test de integración: request a tenant Trial activo → pasa; Trial vencido → 402; Enterprise → pasa; ruta `/admin/` con trial vencido → pasa (whitelist)
  - _Requirements: 5.1, 5.2, 5.4, 5.5_
  - _Depends: 2.2_

- [ ] 5. Panel de system admin (P)
  - _Boundary: TenantAdmin, SubscriptionAdmin_

- [ ] 5.1 Implementar TenantAdmin con gestión de plan
  - Crear `TenantAdmin` con `list_display = [nombre_empresa, subdominio, plan_actual, estado_acceso, trial_expires_at, num_licencias]` y filtros por plan
  - Implementar acción `change_to_enterprise`: valida `num_licencias > 0`, actualiza `Subscription.plan = enterprise`, `fecha_fin = None`, `num_licencias = N`
  - Solo usuarios con `is_staff=True` y `is_superuser=True` acceden al Django Admin
  - Un superusuario puede cambiar un tenant Trial a Enterprise desde el panel y el acceso del tenant se restaura inmediatamente
  - _Requirements: 3.2, 6.1, 6.2, 6.3, 6.4_

- [ ] 5.2 Implementar SubscriptionAdmin con acciones de gestión
  - Implementar acción `extend_trial`: solicita nueva `fecha_fin` (date picker o input), valida que sea futura, actualiza `Subscription.fecha_fin`
  - Implementar acción `update_license_count`: solicita nuevo `num_licencias`, valida `> 0`, actualiza `Subscription.num_licencias`
  - Implementar validación: si `num_licencias == 0` → error con mensaje "El número de licencias debe ser mayor a cero"
  - Tras extender el trial de un tenant bloqueado, el tenant puede acceder sin reiniciar el servidor
  - _Requirements: 3.3, 3.4, 3.5, 6.2, 6.5_

- [ ] 6. Formulario de registro (frontend)
- [ ] 6.1 Implementar RegisterPage
  - Crear `frontend/src/pages/Register/RegisterPage.tsx` con formulario de tres campos: nombre de empresa, subdominio, email del administrador
  - Validar en frontend: subdominio solo acepta `[a-z0-9-]`; email válido; nombre no vacío
  - Al enviar, llamar a `POST /api/public/tenants/register/` y mostrar mensaje de éxito con la URL del tenant (`{subdominio}.sgca.com`) o error inline por campo si la respuesta es 400/409
  - El formulario es accesible en `sgca.com/register` y completa el flujo de registro exitoso mostrando la URL de acceso
  - _Requirements: 1.1, 1.2, 1.3, 1.5_
  - _Depends: 3.2_

- [ ] 7. Tests de integración y E2E
- [ ] 7.1 Tests de integración del flujo de registro
  - Test: registro exitoso → verifica existencia de Tenant, Domain, Subscription(trial) y schema PostgreSQL en la BD
  - Test: registro con subdominio duplicado → HTTP 409, sin recursos huérfanos
  - Test: registro con subdominio con caracteres inválidos → HTTP 400
  - Test: registro sin campos obligatorios → HTTP 400 con errores por campo
  - Todos los tests pasan con `pytest` y schemas de test aislados
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.3_

- [ ] 7.2 Tests de integración del AccessPolicyMiddleware
  - Test: request a endpoint de tenant con trial activo → HTTP 200 (pasa)
  - Test: request a endpoint de tenant con trial vencido → HTTP 402 con `code: trial_expired`
  - Test: request a `/admin/` con trial vencido → HTTP 200 (whitelist, pasa)
  - Test: request a `/api/public/tenants/register/` con trial vencido → HTTP 200 (whitelist, pasa)
  - Test: request a tenant Enterprise → HTTP 200 (siempre activo)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 7.3 Tests E2E del ciclo completo de tenant
  - Test E2E: registrar tenant → acceder al subdominio → verificar acceso activo
  - Test E2E: trial vence → acceso bloqueado → system admin extiende trial → acceso restaurado
  - Test E2E: system admin cambia Trial a Enterprise → acceso ilimitado sin fecha de vencimiento
  - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.3, 6.1, 6.2_
