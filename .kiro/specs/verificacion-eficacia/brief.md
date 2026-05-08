# Brief: verificacion-eficacia

## Problem
Una acción puede cerrarse y parecer resuelta, pero meses después el problema puede reaparecer. Sin verificación de eficacia programada, el sistema no garantiza que las acciones correctivas realmente funcionaron a largo plazo, lo que invalida su propósito para auditorías.

## Current State
Greenfield. Acciones con estado "Verificado" existen (Wave 2), pero no hay mecanismo para programar ni registrar verificaciones futuras de eficacia.

## Desired Outcome
- Al cerrar una acción, el sistema programa automáticamente verificaciones a 6 meses, 1 año y 2 años desde la fecha de cierre
- Cuando llega la fecha, el verificador recibe notificación para realizar la verificación
- El verificador registra si la acción fue eficaz o no, con evidencia y comentarios
- Si una verificación indica no eficaz, se puede generar un nuevo issue vinculado
- El admin puede ver el historial de verificaciones de cualquier acción

## Approach
Modelo VerificacionEficacia con FK a Accion (fecha programada, fecha real, resultado: eficaz/no_eficaz/pendiente, verificador FK, notas). Señal Django en el cambio de estado "Cerrado" que crea automáticamente 3 registros de VerificacionEficacia. Tarea Celery Beat diaria que detecta verificaciones con fecha_programada == hoy y emite evento para que notificaciones envíe el email. Formulario/endpoint para que el verificador registre el resultado.

## Scope
- **In**: Modelo VerificacionEficacia (fecha_programada, fecha_real, resultado, verificador, notas, evidencia), creación automática de 3 verificaciones al cerrar acción (+6m/+12m/+24m), tarea Celery Beat de detección diaria, endpoint de registro de resultado (verificador), opción de crear nuevo Issue si resultado es "no eficaz", historial de verificaciones por acción, permisos (solo verificador puede registrar resultado; admin/supervisor pueden ver historial)
- **Out**: El envío del email de notificación en sí (→ notificaciones coordina el envío), almacenamiento de evidencia adjunta (usa infraestructura de → planes-trabajo), la transición a estado "Verificado" de la Accion (→ acciones)

## Boundary Candidates
- Modelo VerificacionEficacia y lógica de programación automática al cerrar acción
- Tarea Celery Beat de detección de verificaciones próximas
- Endpoint de registro de resultado por el verificador
- Flujo "no eficaz → crear nuevo Issue"

## Out of Boundary
- El email de notificación de verificación próxima (→ notificaciones recibe el evento y envía el email)
- La máquina de estados de la Accion principal (→ acciones)
- El upload de evidencia de verificación (usa el mismo modelo/infra que → planes-trabajo)

## Upstream / Downstream
- **Upstream**: acciones (señal en cambio a estado "Cerrado" dispara la programación), auth-rbac (rol verificador)
- **Downstream**: issues (puede generar nuevo Issue si resultado es "no eficaz"), notificaciones (recibe evento de verificación próxima para enviar email)

## Existing Spec Touchpoints
- **Extends**: N/A
- **Adjacent**: notificaciones — seam de coordinación: verificacion-eficacia detecta la fecha y emite el evento; notificaciones envía el email. acciones — seam: la programación se dispara al cambiar estado a "Cerrado" (no a "Verificado").

## Constraints
- Las 3 verificaciones se programan desde la fecha de cierre: +6 meses, +12 meses, +24 meses
- Solo el rol Verificador puede registrar el resultado de una verificación
- Celery Beat compartido con notificaciones — coordinar schedules para evitar colisiones
- Los modelos heredan de TenantModel (django-tenants)
