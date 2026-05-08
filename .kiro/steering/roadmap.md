# Roadmap — SGCA SaaS

## Overview
SGCA es un SaaS multi-tenant para gestión del ciclo de vida completo de acciones correctivas, preventivas y de mejora derivadas de eventos de seguridad industrial. El sistema permite registrar incidentes, generar acciones con análisis de causa raíz (Ishikawa), asignar responsables, hacer seguimiento con planes de trabajo, subir evidencias y verificar eficacia a largo plazo.

El desarrollo sigue un enfoque wave-by-wave con un solo desarrollador. Cada wave entrega valor incremental y es completamente funcional antes de iniciar la siguiente. Las waves se completan en orden: Wave 1 → Wave 2 → Wave 3 → Wave 4.

## Approach Decision
- **Chosen**: Descomposición por dominio de negocio en 8 specs / 4 waves
- **Why**: Cada spec tiene responsabilidad clara y puede ser especificada, implementada y revisada de forma independiente. Las dependencias entre waves son explícitas y unidireccionales. Favorece revisión adversarial por spec antes de avanzar.
- **Rejected alternatives**:
  - Spec monolítica única (demasiadas tareas, difícil de revisar y hacer seguimiento)
  - Slices verticales amplios (difuminan fronteras de responsabilidad, dificultan reviews)

## Scope
- **In**: Tenant onboarding, autenticación RBAC, issues con Ishikawa, acciones correctivas/preventivas/mejora, planes de trabajo, evidencias, notificaciones por email, verificación de eficacia, reportes PDF/Excel, dashboard
- **Out**: Pagos, facturación, Stripe, Plan Free, Plan Pro, upgrades automáticos, SSO/OAuth, notificaciones in-app, SMS

## Constraints
- Solo desarrollador — completar Wave N antes de iniciar Wave N+1
- Stack fijo: Django 5 + DRF + PostgreSQL 16 + django-tenants + React 18 + Vite + TailwindCSS + Celery + Redis + S3/MinIO + SendGrid + ReportLab + openpyxl + Recharts
- Todas las specs en español
- Los modelos de negocio heredan de TenantModel (django-tenants) — nunca mezclar datos entre tenants

## Boundary Strategy
- **Why this split**: Cada spec mapea a una app Django y un módulo frontend. Las fronteras evitan que un cambio en una spec rompa otra. Los specs dentro de una misma wave pueden desarrollarse secuencialmente con clara separación de responsabilidades.
- **Shared seams to watch**:
  - `tenant-onboarding` y `auth-rbac` comparten el schema público de django-tenants
  - `acciones` y `planes-trabajo`: ¿puede cerrarse una acción sin plan completado? (definir en requirements de acciones)
  - `notificaciones` y `verificacion-eficacia` comparten Celery Beat — cuidar conflictos de schedules
  - `notificaciones` se engancha a eventos de múltiples specs (signals de Django)

## Specs (dependency order)

### Wave 1 — Foundation
- [x] tenant-onboarding — Registro de tenant, subdominio, planes Trial/Enterprise, panel de system admin. Dependencies: none
- [x] auth-rbac — JWT auth, 4 roles (Admin/Responsable/Supervisor/Verificador), gestión de usuarios por tenant. Dependencies: tenant-onboarding

### Wave 2 — Core Business Objects
- [x] issues — Registro de eventos (incidente/casi incidente/reunión), análisis Ishikawa, ciclo de vida del issue. Dependencies: auth-rbac
- [x] acciones — Creación de acciones desde issues, máquina de estados, asignación de responsables, historial de auditoría. Dependencies: issues

### Wave 3 — Execution Layer
- [x] planes-trabajo — Plan de trabajo: actividades, deadlines, subida de evidencias a S3/MinIO. Dependencies: acciones

### Wave 4 — Automation & Intelligence
- [x] notificaciones — Emails vía Celery/SendGrid, detección de deadlines (3d/1d/vencido), resumen semanal. Dependencies: planes-trabajo
- [x] verificacion-eficacia — Verificaciones programadas a 6m/1a/2a al cerrar una acción, workflow de verificador. Dependencies: acciones
- [x] reportes-dashboard — PDF/Excel en background con ReportLab/openpyxl, Recharts dashboard. Dependencies: planes-trabajo
