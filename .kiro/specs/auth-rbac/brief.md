# Brief: auth-rbac

## Problem
Los usuarios de cada empresa necesitan autenticarse de forma segura y el sistema debe controlar qué acciones puede realizar cada rol sin mezclar datos entre tenants.

## Current State
Greenfield. El tenant existe (creado por tenant-onboarding) pero no hay usuarios, autenticación ni permisos.

## Desired Outcome
- Los usuarios se autentican con JWT dentro de su tenant (subdominio)
- Cada usuario tiene exactamente un rol: Admin, Responsable, Supervisor o Verificador
- El admin del tenant puede crear, editar y desactivar usuarios hasta el límite de licencias del plan
- Los endpoints verifican automáticamente el tenant activo y el rol del usuario en cada request

## Approach
djangorestframework-simplejwt para JWT con access/refresh tokens. Custom user model heredando de AbstractUser con campos role y tenant FK. Middleware que inyecta el tenant activo vía subdominio en cada request. Mixins/decoradores de permiso por rol reutilizables en todos los specs posteriores.

## Scope
- **In**: Custom user model con rol (admin/responsable/supervisor/verificador), registro/login/refresh/logout JWT, CRUD de usuarios por el admin del tenant, validación de límite de licencias al activar usuario, middleware de tenant en request, mixins de permiso por rol, cambio de contraseña, endpoint de perfil propio
- **Out**: Recuperación de contraseña por email (→ notificaciones, Wave 4), SSO/OAuth, 2FA, notificaciones de bienvenida

## Boundary Candidates
- Autenticación JWT (login, refresh, logout)
- Custom user model con roles
- CRUD de usuarios (solo admin del tenant)
- Middleware de tenant routing + enforcement de permisos

## Out of Boundary
- Registro del tenant en sí (→ tenant-onboarding)
- Emails de notificación al crear usuario (→ notificaciones)
- Cualquier funcionalidad de negocio (issues, acciones, etc.)

## Upstream / Downstream
- **Upstream**: tenant-onboarding (schema del tenant debe existir; modelo Tenant disponible en schema público)
- **Downstream**: Todos los specs de Wave 2+ dependen de auth-rbac para autenticar requests y verificar permisos por rol

## Existing Spec Touchpoints
- **Extends**: N/A
- **Adjacent**: tenant-onboarding — comparte schema público; el límite de licencias viene del modelo Subscription creado en tenant-onboarding

## Constraints
- Argon2 para cifrado de contraseñas (definido en tech.md)
- JWT con access + refresh tokens; sin cookies de sesión
- El número de usuarios activos no puede exceder el límite de licencias del plan Enterprise
- Un usuario pertenece a exactamente un tenant
