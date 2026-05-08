# Implementation Plan — auth-rbac

- [ ] 1. Configuración base del proyecto para autenticación
- [ ] 1.1 Configurar Django settings para auth-rbac
  - Añadir `AUTH_USER_MODEL = 'users.CustomUser'` en `base.py` (debe hacerse antes de cualquier migración)
  - Añadir `Argon2PasswordHasher` como primer hasher en `PASSWORD_HASHERS`
  - Configurar `SIMPLE_JWT`: `ACCESS_TOKEN_LIFETIME=timedelta(minutes=15)`, `REFRESH_TOKEN_LIFETIME=timedelta(days=7)`, `ROTATE_REFRESH_TOKENS=False`, `BLACKLIST_AFTER_ROTATION=False`
  - Añadir `rest_framework_simplejwt.token_blacklist` y `'users'` a `INSTALLED_APPS`/`TENANT_APPS`
  - Añadir `JWTAuthentication` como `DEFAULT_AUTHENTICATION_CLASS` en `REST_FRAMEWORK` settings
  - `django.test --check` pasa sin errores de configuración
  - _Requirements: 1.1, 2.1_

- [ ] 1.2 Scaffold de la app `users`
  - Crear `backend/apps/users/` con `__init__.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `permissions.py`, `services.py`, `tokens.py`
  - Crear `backend/apps/users/tests/__init__.py` con archivos `test_auth.py`, `test_users.py`, `test_permissions.py` vacíos pero ejecutables
  - Incluir la app en las URLs del tenant (`urls_tenant.py`)
  - `python manage.py check` pasa en el contexto del schema del tenant
  - _Requirements: 2.1_

- [ ] 2. Modelo CustomUser
- [ ] 2.1 Implementar CustomUser con rol y autenticación por email
  - Definir `CustomUser(AbstractUser)`: campo `email` como `USERNAME_FIELD`, deshabilitar `username`, añadir `nombre_completo` y `role` con choices de 4 valores
  - `email` con `unique=True`; `role` no puede ser null ni vacío
  - Generar y aplicar la migración inicial del modelo (`makemigrations users`)
  - `pytest apps/users/tests/test_auth.py::test_user_model` verifica que `is_active=False` impide el login y que `role` acepta solo los 4 valores válidos
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 3. Autenticación JWT
- [ ] 3.1 Serializer de token con claims de rol y tenant
  - Implementar `CustomTokenObtainPairSerializer(TokenObtainPairSerializer)` que añade `role` y `tenant` (schema activo) al payload del JWT
  - El claim `tenant` lee `connection.schema_name` de django-tenants en el momento del login
  - Test unitario: token generado para un usuario con rol `supervisor` incluye `{"role": "supervisor", "tenant": "<schema>"}` en el payload decodificado
  - _Requirements: 1.1, 1.7_
  - _Boundary: CustomTokenObtainPairSerializer_

- [ ] 3.2 Vistas JWT: login, refresh y logout
  - `LoginView`: extiende `TokenObtainPairView` con `CustomTokenObtainPairSerializer`; retorna 401 con mensaje genérico para credenciales incorrectas o usuario inactivo (no revela cuál campo falla)
  - `RefreshView`: extiende `TokenRefreshView`; retorna 401 cuando el refresh token está expirado o en la blacklist
  - `LogoutView`: recibe `{refresh}`, llama `RefreshToken(token).blacklist()` e invalida el token; retorna 204
  - `POST /api/auth/login/` con credenciales correctas retorna `{access, refresh}` 200
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  - _Boundary: LoginView, LogoutView, RefreshView_

- [ ] 3.3 URL routing de autenticación
  - Registrar `POST /api/auth/login/`, `POST /api/auth/refresh/`, `POST /api/auth/logout/` en `urls_tenant.py`
  - Los endpoints son alcanzables en `{subdominio}.sgca.com/api/auth/...`
  - _Requirements: 1.1_

- [ ] 4. Clases de permiso por rol (P)
- [ ] 4.1 (P) Implementar RequireRole e IsAdminTenant
  - `RequireRole(*roles)`: `BasePermission` que verifica `request.user.role in roles`; retorna 403 si el rol no cumple y 401 si el usuario no está autenticado
  - `IsAdminTenant`: shortcut para `RequireRole('admin')`
  - Ambas clases exportadas desde `apps.users.permissions` para ser importadas por specs Wave 2+
  - Test: `RequireRole('admin')` permite rol admin, rechaza responsable (403), rechaza anónimo (401)
  - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - _Boundary: RequireRole, IsAdminTenant_
  - _Depends: 2.1_

- [ ] 5. Servicio de gestión de usuarios
- [ ] 5.1 Implementar UserManagementService con validación de licencias
  - Métodos: `create_user()`, `update_user()`, `deactivate_user()`, `_check_license_limit()`
  - `_check_license_limit()`: para plan Enterprise, lee `Subscription.num_licencias` del schema público con `connection.set_schema_to_public()` y restaura el schema del tenant; lanza `LicenseLimitExceededError` si `activos >= num_licencias`; para plan Trial no verifica
  - `deactivate_user()`: cambia `is_active=False` sin eliminar datos ni historial
  - Test: crear usuario cuando límite Enterprise está alcanzado → `LicenseLimitExceededError`; plan Trial → sin restricción
  - _Requirements: 3.2, 3.4, 4.1, 4.2, 4.3_
  - _Boundary: UserManagementService_
  - _Depends: 4.1_

- [ ] 6. API de gestión de usuarios
- [ ] 6.1 Implementar UserManagementViewSet
  - Endpoints: `GET /api/users/`, `POST /api/users/`, `GET /api/users/{id}/`, `PUT /api/users/{id}/`, `POST /api/users/{id}/deactivate/`
  - Todos los endpoints requieren `IsAdminTenant`; los queries filtran implícitamente por el schema activo (sin filtro manual por tenant)
  - `POST /api/users/` retorna 400 con `{"detail": "..."}` cuando `LicenseLimitExceededError`; 404 cuando el usuario no existe en el tenant activo
  - `GET /api/users/` retorna lista con `id, nombre_completo, email, role, is_active` para todos los usuarios del tenant
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - _Boundary: UserManagementViewSet_
  - _Depends: 5.1_

- [ ] 7. API de perfil propio (P)
- [ ] 7.1 (P) Implementar ProfileView y ChangePasswordView
  - `GET/PUT /api/users/me/`: retorna y actualiza `nombre_completo` y `email` del usuario autenticado; rechaza email duplicado en el tenant con 400
  - `PUT /api/users/me/change-password/`: valida `current_password` (401 si incorrecto), actualiza contraseña con Argon2; retorna 200 vacío
  - Ambos endpoints accesibles para cualquier rol autenticado (no solo admin)
  - `GET /api/users/me/` retorna los datos actualizados inmediatamente después de un `PUT`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - _Boundary: ProfileView, ChangePasswordView_
  - _Depends: 2.1_

- [ ] 8. Tests de integración y E2E
- [ ] 8.1 (P) Tests de autenticación JWT
  - Login exitoso retorna access + refresh con claims `role` y `tenant`
  - Login con contraseña incorrecta → 401 (mismo mensaje que email incorrecto, no revela cuál falló)
  - Login con usuario `is_active=False` → 401
  - Refresh con token válido → nuevo access token
  - Refresh con token en blacklist (post-logout) → 401
  - Aislamiento: mismo email en dos schemas distintos → usuario A no puede autenticarse en tenant B
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
  - _Boundary: LoginView, LogoutView, RefreshView_
  - _Depends: 3.2, 3.3_

- [ ] 8.2 (P) Tests de gestión de usuarios y licencias
  - Admin crea usuario → 201; campos inválidos → 400; email duplicado en tenant → 400
  - Admin desactiva usuario → is_active=False; usuario desactivado intenta login → 401
  - Plan Enterprise en límite: crear usuario → 400; desactivar uno → crear otro → 201
  - Plan Trial: crear sin límite (no importa num_licencias)
  - Usuario de otro tenant (id diferente, mismo email) → 404 al intentar operar sobre él
  - Rol no-admin (responsable) intenta GET /api/users/ → 403
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3_
  - _Boundary: UserManagementViewSet, UserManagementService_
  - _Depends: 6.1_

- [ ] 8.3 (P) Tests de permisos y perfil
  - `RequireRole('supervisor')` permite supervisor, rechaza admin → 403, rechaza anónimo → 401
  - `IsAdminTenant` permite admin, rechaza los otros 3 roles → 403
  - `GET /api/users/me/` retorna datos del usuario autenticado
  - `PUT /api/users/me/change-password/` con contraseña actual correcta → 200; incorrecta → 400
  - `PUT /api/users/me/` con email en uso por otro usuario del mismo tenant → 400
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5_
  - _Boundary: RequireRole, IsAdminTenant, ProfileView, ChangePasswordView_
  - _Depends: 7.1_
