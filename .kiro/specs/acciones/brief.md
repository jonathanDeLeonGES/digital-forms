# Brief: acciones

## Problem
Después de registrar un incidente, las empresas necesitan gestionar formalmente las acciones de respuesta, asignar responsables y hacer seguimiento del estado hasta verificar que la acción fue efectiva. Sin trazabilidad, no se puede auditar el cumplimiento.

## Current State
Greenfield. Issues implementados (Wave 2, primera spec). Los issues pueden existir sin acciones generadas.

## Desired Outcome
- Desde un issue se pueden crear una o más acciones de tipo correctiva, preventiva o de mejora
- Cada acción tiene responsable, fecha límite y descripción del resultado esperado
- La acción transita por estados con validación de rol: Abierto → En proceso → Cerrado → Verificado
- Cada cambio de estado queda registrado en historial con actor y timestamp (requerimiento de auditoría)
- El admin ve todas las acciones del tenant; responsable ve las propias; supervisor puede gestionar el cierre

## Approach
Modelo Accion con FK a Issue y FK a User (responsable). Máquina de estados con validaciones de rol por transición. Tabla HistorialEstado separada para auditoría completa (accion, estado_anterior, estado_nuevo, usuario, timestamp, comentario). API REST con DRF. Señales Django para disparar eventos downstream (notificaciones, verificacion-eficacia).

## Scope
- **In**: CRUD de acciones (tipo: correctiva/preventiva/mejora), FK a Issue obligatoria, asignación de responsable, fecha límite, máquina de estados con validación de rol por transición, tabla HistorialEstado (auditoría), listado y filtros (estado/tipo/responsable/área), permisos por rol
- **Out**: Plan de trabajo con actividades (→ planes-trabajo), subida de evidencias (→ planes-trabajo), verificación de eficacia programada (→ verificacion-eficacia), emails de cambio de estado (→ notificaciones), reportes (→ reportes-dashboard)

## Boundary Candidates
- Modelo y CRUD de Accion
- Máquina de estados con reglas de rol por transición
- Tabla HistorialEstado (auditoría completa)
- API de listado con filtros

## Out of Boundary
- Plan de trabajo de la acción (→ planes-trabajo)
- Programación de verificación futura al cerrar (→ verificacion-eficacia)
- Emails de notificación al cambiar estado (→ notificaciones)

## Upstream / Downstream
- **Upstream**: issues (FK obligatoria a Issue), auth-rbac (roles para validar transiciones)
- **Downstream**: planes-trabajo (FK Accion en PlanTrabajo), verificacion-eficacia (escucha cierre de acción para programar verificaciones), notificaciones (escucha cambios de estado), reportes-dashboard (agrega datos de acciones)

## Existing Spec Touchpoints
- **Extends**: N/A
- **Adjacent**: issues — seam claro: issues registra evento + Ishikawa; acciones registra la respuesta formal. planes-trabajo — seam a definir en requirements: ¿puede cerrarse una acción (En proceso → Cerrado) si el plan de trabajo no está completo?

## Constraints
- Tabla historial_estados requerida para auditoría (definida en tech.md)
- Reglas de transición de estado:
  - Abierto → En proceso: responsable asignado
  - En proceso → Cerrado: supervisor
  - Cerrado → Verificado: verificador
- Los modelos heredan de TenantModel (django-tenants)
