# Research & Design Decisions — tenant-onboarding

## Summary
- **Feature**: `tenant-onboarding`
- **Discovery Scope**: New Feature (greenfield)
- **Key Findings**:
  - django-tenants 4.x proporciona schema-per-tenant out-of-the-box y es el mecanismo de aislamiento definitivo
  - Django Admin extendido es suficiente para el panel de system admin en MVP — evita construir un frontend dedicado
  - El middleware de acceso debe ejecutarse después de TenantMiddleware y antes de las vistas; la whitelist de rutas públicas es el riesgo principal de esta capa

## Research Log

### django-tenants: Schema-per-tenant con PostgreSQL
- **Context**: El stack define django-tenants como mecanismo de multi-tenancy
- **Findings**:
  - django-tenants 4.x requiere que el modelo Tenant extienda `TenantMixin` y Domain extienda `DomainMixin`
  - `auto_create_schema = True` en el modelo Tenant activa la creación automática del schema al `save()`
  - Las migraciones de apps en `TENANT_APPS` se aplican automáticamente al nuevo schema
  - El schema público contiene solo los modelos en `SHARED_APPS`; los modelos de negocio en `TENANT_APPS`
- **Implications**: No se necesita código custom para la creación del schema — django-tenants lo maneja. El riesgo es la atomicidad: si el schema se crea pero la Subscription falla, hay que hacer rollback manual del tenant.

### Django Admin para System Admin Panel
- **Context**: Evaluar si Django Admin es suficiente vs. construir un panel React custom
- **Findings**:
  - Django Admin soporta acciones personalizadas (change_plan, extend_trial, set_licenses) via `ModelAdmin.actions`
  - Solo usuarios con `is_staff=True` y `is_superuser=True` acceden al admin por defecto
  - Suficiente para MVP con un único system admin técnico
- **Implications**: Cero código frontend para el panel de admin. Las acciones de negocio se implementan como Django Admin actions.

### Access Policy Middleware
- **Context**: Bloqueo de acceso para trials vencidos
- **Findings**:
  - El middleware debe ejecutarse DESPUÉS de TenantMiddleware (necesita `request.tenant`)
  - Las rutas del Django Admin y el endpoint de registro deben ser whitelisted para no bloquearse a sí mismas
  - Retornar JSON 402 para API requests; redirección para requests de browser (distinguir por Accept header)

## Architecture Pattern Evaluation

| Opción | Descripción | Fortalezas | Riesgos |
|--------|-------------|-----------|---------|
| Schema-per-tenant (django-tenants) | Un schema PostgreSQL por empresa | Aislamiento máximo, sin filtros en queries | Límite práctico ~1000 tenants por instancia PostgreSQL |
| Shared schema con tenant_id | Una sola BD con columna tenant_id en todas las tablas | Más simple, escala a más tenants | Riesgo de data leak si falta un filtro; no cumple el requisito de aislamiento del brief |
| Database-per-tenant | Una BD PostgreSQL por empresa | Aislamiento total | Complejidad operacional excesiva para MVP |

**Seleccionado**: Schema-per-tenant vía django-tenants (definido en tech.md).

## Design Decisions

### Decision: Django Admin como panel de system admin
- **Context**: Se necesita un panel para que el system admin gestione tenants sin acceder directamente a la BD
- **Alternatives Considered**:
  1. Django Admin extendido — acciones custom para cambiar plan, asignar licencias, extender trial
  2. Endpoint REST protegido por `is_superuser` + frontend React dedicado
- **Selected Approach**: Django Admin extendido con ModelAdmin y actions personalizadas
- **Rationale**: MVP con un solo system admin técnico; cero código frontend adicional; seguridad built-in
- **Trade-offs**: UI menos amigable que un panel custom, pero suficiente para el volumen esperado
- **Follow-up**: Si el número de system admins crece o se necesita UI no técnica, migrar a panel React en Wave 5+

### Decision: Atomicidad del registro de tenant
- **Context**: La creación del tenant involucra múltiples pasos: Tenant, Domain, schema, Subscription
- **Alternatives Considered**:
  1. `@transaction.atomic` — funciona para los modelos en el schema público, pero la creación del schema PostgreSQL es una operación DDL que no se puede hacer rollback dentro de una transacción de Django
  2. Try/except con cleanup manual — si falla la Subscription, eliminar el Tenant (lo que borra el schema por `auto_drop_schema`)
- **Selected Approach**: Try/except con cleanup explícito: si cualquier paso falla después de crear el Tenant, llamar a `tenant.delete()` que invoca `auto_drop_schema = True`
- **Rationale**: Las operaciones DDL (CREATE SCHEMA) en PostgreSQL hacen auto-commit; el cleanup vía delete() es la forma recomendada por django-tenants
- **Follow-up**: Verificar en tests que `tenant.delete()` limpia el schema correctamente en todos los escenarios de fallo

### Decision: Registro de tenant por API REST (no solo admin)
- **Context**: La spec incluye el flujo de registro de nuevas empresas
- **Selected Approach**: Endpoint público `POST /api/public/tenants/register/` — sin autenticación requerida
- **Rationale**: Las empresas se registran antes de tener usuarios; el endpoint es el punto de entrada al sistema
- **Trade-offs**: Riesgo de spam/abuse — mitigar con rate limiting en Nginx (fuera del scope de esta spec)

## Risks & Mitigations
- **Schema creation failure** — Si `auto_create_schema` falla (ej. permisos PostgreSQL), el tenant queda registrado sin schema. Mitigation: try/except + cleanup explícito.
- **Subdomain collision race condition** — Dos registros simultáneos con el mismo subdominio pueden pasar la validación de unicidad antes de que cualquiera haga commit. Mitigation: unique constraint en el modelo Domain + manejo del IntegrityError.
- **Whitelist de middleware incompleta** — Si el AccessPolicyMiddleware bloquea la ruta de registro o el Django Admin, el sistema se bloquea a sí mismo. Mitigation: tests de integración específicos para las rutas públicas.

## References
- django-tenants documentation: https://django-tenants.readthedocs.io/
- PostgreSQL schema isolation: aislamiento por schema nativo de PostgreSQL, sin configuración adicional
