# Brief: notificaciones

## Problem
Los responsables olvidan sus deadlines, los supervisores no saben cuándo deben revisar acciones y el admin no tiene visibilidad del estado global. Sin notificaciones automáticas, el sistema pierde efectividad operativa.

## Current State
Greenfield. planes-trabajo implementado (Wave 3). Todos los datos existen pero no hay sistema de notificaciones.

## Desired Outcome
- Los responsables reciben email cuando se les asigna una acción o actividad
- Los responsables y supervisores reciben alertas a 3 días, 1 día y cuando un deadline vence
- Los supervisores reciben notificación cuando una acción pasa a "Cerrado" para su revisión
- El verificador recibe notificación cuando hay acciones en "Cerrado" pendientes de verificación de eficacia
- El admin recibe resumen semanal del estado de todas las acciones del tenant
- Celery Beat detecta deadlines diariamente y envía los emails correspondientes

## Approach
Celery + Redis para tareas asíncronas y scheduled. SendGrid con plantillas HTML personalizadas por tipo de notificación. Señales Django para eventos síncronos (asignación, cambio de estado) que disparan tareas Celery. Celery Beat con tarea diaria de deadline scanning de Actividades. Tarea semanal de resumen al admin.

## Scope
- **In**: Email de asignación de acción/actividad, emails de deadline próximo (3d/1d/vencido) para Actividades, email a supervisor cuando acción pasa a "Cerrado", email a verificador cuando hay acciones pendientes de verificación, resumen semanal al admin, tareas Celery async, Celery Beat schedules (diario y semanal), plantillas HTML SendGrid, preferencias de notificación por usuario (activar/desactivar tipos)
- **Out**: Notificaciones in-app/push, SMS, Slack/Teams, programación de verificaciones de eficacia (→ verificacion-eficacia), historial de emails enviados detallado (nice-to-have)

## Boundary Candidates
- Envío de emails vía SendGrid API
- Tareas Celery para envío asíncrono (fire-and-forget)
- Celery Beat: tarea diaria de deadline scanning
- Celery Beat: tarea semanal de resumen
- Plantillas HTML de email por tipo

## Out of Boundary
- Programación de verificaciones de eficacia a futuro (→ verificacion-eficacia, también usa Celery Beat)
- Generación de reportes PDF/Excel en background (→ reportes-dashboard)

## Upstream / Downstream
- **Upstream**: planes-trabajo (modelo Actividad con deadlines), acciones (cambios de estado via señales), auth-rbac (emails y roles de usuarios)
- **Downstream**: ninguno directo en MVP

## Existing Spec Touchpoints
- **Extends**: N/A
- **Adjacent**: verificacion-eficacia — ambas usan Celery Beat; coordinar para evitar conflictos de schedules. reportes-dashboard — también usa Celery para generación async.

## Constraints
- SendGrid como único proveedor de email (definido en tech.md)
- Celery + Redis como broker (definido en tech.md)
- Las tareas Celery deben ser idempotentes (retry-safe con task IDs)
- No enviar emails a usuarios desactivados
- Los modelos de preferencias de notificación son por tenant (TenantModel)
