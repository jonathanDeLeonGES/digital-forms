# Brief: planes-trabajo

## Problem
Una vez creada una acción, el responsable necesita un plan concreto con actividades, deadlines y evidencias que demuestren ejecución real. Sin plan, la acción es solo una intención sin seguimiento.

## Current State
Greenfield. Acciones implementadas (Wave 2). Una acción existe con responsable asignado pero sin plan de actividades ni evidencias.

## Desired Outcome
- Cada acción tiene un Plan de Trabajo con una o más actividades
- Cada actividad tiene descripción, responsable, fecha límite y estado (pendiente/en proceso/completada)
- El responsable puede subir evidencias (archivos: PDF, imagen, video) a cada actividad
- Los archivos se almacenan en S3/MinIO con carpetas separadas por tenant
- El progreso del plan (% completado) se calcula automáticamente
- El supervisor puede ver el plan y todas las evidencias antes de aprobar el cierre de la acción

## Approach
Modelo PlanTrabajo (1:1 con Accion), Actividad (FK a PlanTrabajo con estado), Evidencia (FK a Actividad con archivo). Upload multipart con django-storages hacia S3/MinIO. URLs firmadas para acceso seguro a evidencias. Cálculo de progreso: actividades completadas / total actividades. API REST con DRF.

## Scope
- **In**: CRUD de PlanTrabajo y Actividades, estados de actividad (pendiente/en proceso/completada), upload de archivos a S3/MinIO (PDF/JPG/PNG/MP4), listado de evidencias por actividad, cálculo de progreso del plan, permisos por rol, URLs firmadas para descarga segura, carpetas por tenant en S3 (`{tenant-slug}/evidencias/`)
- **Out**: Notificaciones de deadline próximo (→ notificaciones), generación de reporte PDF del plan (→ reportes-dashboard), programación de verificación de eficacia (→ verificacion-eficacia)

## Boundary Candidates
- Modelos PlanTrabajo, Actividad y Evidencia
- Upload y storage en S3/MinIO con django-storages
- Cálculo de progreso del plan
- API de listado, detalle y descarga

## Out of Boundary
- La máquina de estados de la Accion (→ acciones)
- Emails de deadline próximo o vencido (→ notificaciones)
- Generación de PDF/Excel del plan (→ reportes-dashboard)

## Upstream / Downstream
- **Upstream**: acciones (FK obligatoria PlanTrabajo → Accion), auth-rbac (permisos)
- **Downstream**: notificaciones (lee Actividades con deadline próximo para enviar alertas), reportes-dashboard (agrega datos de progreso), verificacion-eficacia (puede requerir evidencia de verificación)

## Existing Spec Touchpoints
- **Extends**: N/A
- **Adjacent**: acciones — seam clave: ¿puede una Accion transitar a "Cerrado" si el plan no tiene todas las actividades completadas? A definir en requirements. notificaciones — lee el modelo Actividad directamente para el deadline scanning.

## Constraints
- Almacenamiento: MinIO en desarrollo local, S3 en producción (django-storages abstrae la diferencia)
- Carpetas S3: `s3://bucket/{tenant-slug}/evidencias/` (definido en tech.md)
- Tipos de archivo aceptados: PDF, JPG, PNG, MP4 (confirmar límites en requirements)
- URLs de S3 deben ser firmadas (no acceso público directo)
- Los modelos heredan de TenantModel (django-tenants)
