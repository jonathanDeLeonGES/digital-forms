# Brief: issues

## Problem
Las empresas no tienen forma estructurada de registrar eventos de seguridad y analizar sus causas raíz de manera trazable y auditable. Los incidentes se registran en Excel o papel sin seguimiento.

## Current State
Greenfield. Auth y tenants funcionan (Wave 1 completa). No hay modelos de negocio aún.

## Desired Outcome
- Cualquier usuario autenticado puede registrar un evento de seguridad (incidente, casi incidente, reunión)
- El análisis de causa raíz se captura mediante Diagrama de Ishikawa con 6 categorías fijas y causas/subcausas
- El issue tiene ciclo de vida: Abierto → En Análisis → Acciones Generadas → Cerrado
- Admins y supervisores ven todos los issues del tenant; responsables ven los propios

## Approach
Modelo Issue con FK a User (reportado_por) y campos de clasificación. Modelo CausaRaiz con estructura categoría → causas → subcausas vinculado al Issue. API REST con DRF. Frontend con formulario multi-sección para captura del Ishikawa.

## Scope
- **In**: CRUD de issues (tipo: incidente/casi incidente/reunión de seguridad), campos (título, descripción, fecha, área, gravedad), análisis Ishikawa (6 categorías fijas + causas + subcausas), estados del issue, filtros y listado paginado por tenant, permisos por rol
- **Out**: Generación de acciones desde el issue (→ acciones), adjuntos/evidencias en el issue (→ planes-trabajo), reportes PDF del análisis (→ reportes-dashboard), notificaciones al crear issue (→ notificaciones)

## Boundary Candidates
- Modelo y CRUD de Issue
- Modelo y CRUD de Diagrama Ishikawa (categorías + causas + subcausas)
- Máquina de estados del Issue
- API de listado con filtros y paginación

## Out of Boundary
- Creación de acciones correctivas/preventivas a partir del issue (→ acciones)
- Generación de PDF del análisis Ishikawa (→ reportes-dashboard)
- Notificaciones por email al crear o actualizar issue (→ notificaciones)

## Upstream / Downstream
- **Upstream**: auth-rbac (autenticación, roles, permisos por tenant)
- **Downstream**: acciones (FK Issue obligatoria en el modelo Accion; un issue puede generar múltiples acciones)

## Existing Spec Touchpoints
- **Extends**: N/A
- **Adjacent**: acciones — seam clave: issues termina en el registro del evento y el análisis Ishikawa; acciones empieza en la decisión de respuesta

## Constraints
- Los modelos heredan de TenantModel (django-tenants) — nunca mezclar datos entre tenants
- El Diagrama Ishikawa tiene exactamente 6 categorías fijas: Método, Máquina, Material, Mano de Obra, Medición, Medio Ambiente
- Un issue puede existir sin acciones generadas (no es obligatorio generar acciones)
