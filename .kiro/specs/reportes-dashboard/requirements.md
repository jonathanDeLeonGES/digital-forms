# Requirements Document

## Project Description (Input)
Los admins y supervisores de SGCA no tienen visibilidad del estado global de las acciones correctivas, tendencias de incidentes y cumplimiento de planes de trabajo. El sistema ya tiene todos los datos de negocio (acciones, issues, actividades) pero no ofrece vistas agregadas ni exportación de reportes. Se requiere un dashboard en tiempo real con métricas clave (acciones por estado/tipo/área, cumplimiento de deadlines, tendencia mensual de incidentes) y la capacidad de exportar reportes PDF y Excel generados en background (Celery) con notificación al usuario cuando están listos para descarga. Solo los roles admin y supervisor tienen acceso. Gráficas con Recharts (estética Power BI). Fuera del scope: BI externo, almacenamiento permanente de reportes, reportes de verificación de eficacia detallados.

## Introducción
Reportes y Dashboard proveen inteligencia ejecutiva sobre el ciclo de vida de acciones de seguridad del SGCA. Esta especificación cubre únicamente la agregación de datos de solo lectura, la generación asíncrona de reportes PDF/Excel y el dashboard interactivo. Los datos de origen (acciones, issues, actividades) son propiedad de sus respectivas specs y nunca se duplican.

## Boundary Context
- **In scope**: Dashboard de métricas en tiempo real, generación async de PDF (ReportLab) y Excel (openpyxl), almacenamiento temporal en S3, notificación de reporte listo, filtros por fecha/área/estado/tipo, descarga con URL firmada, gestión del estado de reportes generados
- **Out of scope**: Creación o modificación de datos (solo lectura), BI externo (Power BI, Tableau), almacenamiento permanente de reportes, reportes de verificación de eficacia detallados, acceso para roles responsable y verificador
- **Adjacent expectations**: El email de "reporte listo" se envía directamente desde el Celery task de esta spec vía SendGrid (sin pasar por notificaciones); notificaciones spec no necesita conocer este evento. AccionService, IssueService, PlanService se consumen como fuentes de datos de solo lectura vía Django ORM.

## Requirements

### Requirement 1: Dashboard de Métricas en Tiempo Real
**Objective:** As a admin o supervisor, I want ver métricas clave del estado de acciones e incidentes en tiempo real, so that pueda tomar decisiones informadas sin necesidad de generar un reporte completo

#### Acceptance Criteria
1. When admin o supervisor accede al dashboard, the SGCA shall mostrar el conteo de acciones agrupadas por estado (abierto, en proceso, cerrado, verificado)
2. When admin o supervisor accede al dashboard, the SGCA shall mostrar el conteo de acciones agrupadas por tipo (correctiva, preventiva, mejora)
3. When admin o supervisor accede al dashboard, the SGCA shall mostrar el conteo de acciones agrupadas por área (del issue vinculado)
4. When admin o supervisor accede al dashboard, the SGCA shall mostrar el porcentaje de actividades completadas a tiempo vs vencidas
5. When admin o supervisor accede al dashboard, the SGCA shall mostrar la tendencia mensual del número de issues registrados para los últimos 12 meses
6. When admin o supervisor aplica filtros de fecha o área, the SGCA shall actualizar todas las métricas del dashboard según los filtros seleccionados
7. If un usuario con rol responsable o verificador intenta acceder al dashboard, the SGCA shall rechazar el acceso con error 403

---

### Requirement 2: Solicitud de Generación de Reporte PDF
**Objective:** As a admin o supervisor, I want solicitar la generación de un reporte PDF con los datos filtrados, so that pueda compartir reportes formales para auditorías externas

#### Acceptance Criteria
1. When admin o supervisor envía una solicitud de reporte PDF con filtros opcionales (fecha inicio, fecha fin, área, estado, tipo), the SGCA shall registrar la solicitud y encolar la tarea de generación en Celery de forma asíncrona
2. The SGCA shall retornar inmediatamente un ID de reporte con estado "pendiente" sin esperar a que la generación termine
3. When el reporte PDF está listo, the SGCA shall enviar un email al usuario solicitante con el enlace de descarga
4. The SGCA shall incluir en el PDF: resumen de métricas, tabla de acciones con sus detalles, historial de estados
5. If la generación del reporte falla, the SGCA shall marcar el reporte con estado "error" y registrar el fallo en el log del sistema

---

### Requirement 3: Solicitud de Generación de Reporte Excel
**Objective:** As a admin o supervisor, I want solicitar la generación de un reporte Excel con los datos filtrados, so that pueda analizar los datos en hojas de cálculo

#### Acceptance Criteria
1. When admin o supervisor solicita un reporte Excel con filtros opcionales, the SGCA shall encolar la generación asíncrona y retornar un ID de reporte con estado "pendiente"
2. When el reporte Excel está listo, the SGCA shall enviar un email al usuario solicitante con el enlace de descarga
3. The SGCA shall generar el Excel con hojas separadas para: acciones, issues, y métricas resumen
4. If la generación del reporte Excel falla, the SGCA shall marcar el reporte con estado "error"

---

### Requirement 4: Descarga Segura de Reportes Generados
**Objective:** As a admin o supervisor, I want descargar un reporte generado de forma segura, so that pueda acceder al archivo sin exponer rutas S3 directas

#### Acceptance Criteria
1. When admin o supervisor solicita la descarga de un reporte con estado "listo", the SGCA shall generar y retornar una URL firmada de S3 válida por 1 hora
2. If el reporte solicitado tiene estado "pendiente", the SGCA shall informar que el reporte aún está siendo generado
3. If el reporte solicitado tiene estado "expirado", the SGCA shall informar que el reporte debe ser regenerado
4. The SGCA shall garantizar que solo el usuario que solicitó el reporte o un admin pueda descargar ese reporte
5. The SGCA shall no exponer rutas S3 directas en ningún endpoint; todo acceso a archivos es exclusivamente por URL firmada

---

### Requirement 5: Gestión de Estado de Reportes
**Objective:** As a admin o supervisor, I want ver el historial y estado de mis reportes solicitados, so that pueda hacer seguimiento de las solicitudes en progreso y acceder a reportes anteriores

#### Acceptance Criteria
1. When admin o supervisor lista sus reportes, the SGCA shall mostrar para cada uno: tipo (PDF/Excel), estado (pendiente/listo/expirado/error), filtros aplicados, fecha de solicitud
2. The SGCA shall marcar automáticamente como "expirado" todo reporte listo con más de 24 horas desde su generación
3. When admin o supervisor elimina un reporte, the SGCA shall borrar el archivo de S3 y el registro de la base de datos
4. If un admin lista reportes, the SGCA shall mostrar todos los reportes del tenant; si es supervisor, solo sus propios reportes

---

### Requirement 6: Filtros de Reporte y Dashboard
**Objective:** As a admin o supervisor, I want filtrar los datos del dashboard y de los reportes por parámetros clave, so that pueda analizar períodos o áreas específicas

#### Acceptance Criteria
1. The SGCA shall aceptar los siguientes parámetros de filtro opcionales: fecha_inicio (date), fecha_fin (date), area (string), estado_accion (choices), tipo_accion (choices)
2. If fecha_inicio es posterior a fecha_fin, the SGCA shall rechazar la solicitud con error 400 y mensaje descriptivo
3. When no se aplican filtros, the SGCA shall calcular métricas y generar reportes con todos los datos del tenant activo
4. The SGCA shall validar que los valores de estado_accion y tipo_accion correspondan a opciones válidas del sistema
