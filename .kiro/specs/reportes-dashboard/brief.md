# Brief: reportes-dashboard

## Problem
Los admins y supervisores necesitan visibilidad del estado global de acciones, tendencias de incidentes y cumplimiento de planes para tomar decisiones y preparar auditorías. Sin reportes, el sistema es un registro sin inteligencia ejecutiva.

## Current State
Greenfield. planes-trabajo implementado (Wave 3). Todos los datos de negocio existen pero no hay vistas agregadas ni generación de reportes.

## Desired Outcome
- Dashboard con métricas clave: acciones por estado/tipo/área, cumplimiento de deadlines, tendencia de incidentes por mes
- Exportación de reportes PDF y Excel filtrados por rango de fechas, estado, área, tipo
- Los reportes se generan en background (Celery) y el usuario recibe notificación cuando están listos para descarga
- Los gráficos del dashboard usan Recharts con estética tipo Power BI

## Approach
Backend: endpoints de aggregation con Django ORM (COUNT, GROUP BY). Generación de PDF con ReportLab (gráficas embebidas). Generación de Excel con openpyxl. Tareas Celery para generación async; archivo temporal en S3 con URL firmada de duración limitada; notificación al usuario cuando el reporte está listo. Frontend: Recharts para dashboard interactivo con filtros de fecha y área.

## Scope
- **In**: Dashboard con métricas (acciones por estado, tipo, área; deadlines vencidos vs a tiempo; tendencia mensual de issues), generación async de PDF (ReportLab) y Excel (openpyxl), almacenamiento temporal del reporte en S3, notificación de "reporte listo" con URL firmada, filtros (rango de fechas, estado, área, tipo), gráficas Recharts en frontend, permisos (solo admin y supervisor)
- **Out**: BI externo (Power BI, Tableau), exportación en tiempo real sin Celery para datasets grandes, almacenamiento permanente de reportes generados, reportes de verificación de eficacia detallados (extensión futura)

## Boundary Candidates
- Endpoints de aggregation y métricas (Django ORM)
- Generación de PDF (ReportLab)
- Generación de Excel (openpyxl)
- Tareas Celery para generación async
- Dashboard frontend con Recharts

## Out of Boundary
- Los datos de negocio en sí (acciones, issues, planes) — solo agrega, no duplica modelos
- Almacenamiento permanente de reportes (son temporales, se regeneran bajo demanda)

## Upstream / Downstream
- **Upstream**: planes-trabajo, acciones, issues, auth-rbac (todas como fuentes de datos de solo lectura)
- **Downstream**: ninguno en MVP

## Existing Spec Touchpoints
- **Extends**: N/A
- **Adjacent**: notificaciones — usa misma infraestructura Celery y SendGrid para el email de "reporte listo". verificacion-eficacia — fuente de datos adicional para métricas de eficacia a largo plazo.

## Constraints
- ReportLab para PDF, openpyxl para Excel (definido en tech.md)
- Celery + Redis para generación async (definido en tech.md)
- Recharts para gráficas frontend (definido en tech.md)
- Los reportes generados en S3 son temporales — URLs firmadas con expiración (ej. 1 hora)
- Solo roles admin y supervisor tienen acceso a reportes y dashboard
- Los modelos de negocio nunca se duplican — solo se consultan vía ORM
