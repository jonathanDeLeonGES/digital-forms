# Brief: tenant-onboarding

## Problem
Las empresas industriales no tienen forma estructurada de registrarse en SGCA y obtener su espacio aislado. El system admin necesita controlar planes y licencias sin autoservicio de pagos.

## Current State
Proyecto greenfield. No existe código aún. django-tenants está definido en el stack pero no implementado.

## Desired Outcome
- Una empresa puede registrarse y obtener su subdominio/tenant en SGCA con período de prueba de 14 días
- El system admin puede ver todos los tenants, cambiar de Trial a Enterprise, asignar número de licencias y extender fechas de vencimiento
- Los tenants en Trial que vencen pierden acceso sin perder sus datos

## Approach
django-tenants con schema-per-tenant. Schema público: Tenant, Domain, Plan, Subscription. Subdominio como identificador del tenant. Panel de system admin vía Django Admin extendido o endpoint protegido por flag de superusuario.

## Scope
- **In**: Registro de tenant (nombre empresa, subdominio, email admin), creación automática de schema y ejecución de migraciones, modelos Plan (Trial/Enterprise) y Subscription, middleware de identificación de tenant por subdominio, lógica de acceso bloqueado para trials vencidos (HTTP 402 o redirect), panel system admin (listar tenants, cambiar plan, asignar licencias, extender trial)
- **Out**: Autenticación de usuarios (→ auth-rbac), pagos/Stripe, auto-upgrades, UI de onboarding elaborada tipo wizard

## Boundary Candidates
- Creación y migración de schemas (django-tenants core)
- Gestión de planes y suscripciones (lógica de negocio)
- Panel de system admin
- Middleware de tenant routing por subdominio

## Out of Boundary
- Autenticación de usuarios dentro del tenant (→ auth-rbac)
- Gestión de usuarios del tenant (→ auth-rbac)
- Cualquier dato de negocio (issues, acciones, etc.)

## Upstream / Downstream
- **Upstream**: Ninguno. Spec fundacional.
- **Downstream**: auth-rbac depende del modelo Tenant y del schema creado. Todos los specs de Wave 2+ asumen que el tenant routing funciona correctamente.

## Existing Spec Touchpoints
- **Extends**: N/A (greenfield)
- **Adjacent**: auth-rbac — comparte schema público para el modelo de usuario; se implementa inmediatamente después

## Constraints
- django-tenants requiere modelos Tenant y Domain en el schema público
- El subdominio debe ser único globalmente y validado con regex
- Los datos de un tenant nunca deben ser accesibles desde otro tenant
- No hay autoservicio de pagos en MVP
