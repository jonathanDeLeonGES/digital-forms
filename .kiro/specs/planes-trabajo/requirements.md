# Requirements Document

## Project Description (Input)
Una vez creada una acción de seguridad en SGCA, el responsable necesita un plan concreto con actividades específicas, fechas límite y evidencias que demuestren la ejecución real. Actualmente no existe mecanismo para estructurar esta ejecución (proyecto greenfield, Wave 3). Se necesita que cada Accion pueda tener un PlanTrabajo con actividades asignadas a responsables, que los responsables puedan subir evidencias de ejecución (PDF/imagen/video) almacenadas en S3/MinIO por tenant, que el progreso se calcule automáticamente, y que el sistema pueda verificar si el plan está completo para validar el cierre de la acción. Queda fuera: notificaciones de deadline (→ notificaciones), generación de PDF del plan (→ reportes-dashboard), programación de verificaciones de eficacia (→ verificacion-eficacia).

## Introducción
SGCA Planes de Trabajo gestiona la capa de ejecución de las acciones correctivas, preventivas y de mejora. Cada Accion tiene un PlanTrabajo con actividades asignadas a responsables. Las actividades tienen estados (pendiente/en_proceso/completada), fechas límite y pueden recibir evidencias en forma de archivos. El progreso del plan se calcula automáticamente. Esta especificación es la fuente de verdad para la ejecución física de las acciones; la máquina de estados de la Accion es responsabilidad de la spec `acciones`.

## Boundary Context
- **In scope**: CRUD de PlanTrabajo (1:1 con Accion), CRUD de Actividades con estados, subida y descarga de evidencias (archivos) en S3/MinIO, progreso automático del plan, permisos por rol, URLs firmadas para descarga segura, operación de verificación de completitud para AccionService
- **Out of scope**: Notificaciones de deadline próximo (→ notificaciones), generación de reportes PDF/Excel del plan (→ reportes-dashboard), programación de verificaciones de eficacia (→ verificacion-eficacia), la transición de estado de la Accion en sí (→ acciones)
- **Adjacent expectations**: AccionService (spec acciones) llama a `PlanService.is_plan_complete(accion_id)` antes de permitir la transición "En proceso → Cerrado". Notificaciones leerá el modelo Actividad directamente para el deadline scanning vía Celery Beat.

## Requirements

### Requirement 1: Creación del Plan de Trabajo
**Objective:** As admin o supervisor, I want crear un plan de trabajo vinculado a una acción existente, so that el responsable tenga actividades concretas a ejecutar con fechas límite y responsables definidos

#### Acceptance Criteria
1. When un admin o supervisor envía la solicitud de creación de plan con al menos una actividad (descripción, responsable, fecha límite), the SGCA shall crear el PlanTrabajo asociado a la Accion y registrar las actividades con estado "pendiente"
2. If una Accion ya tiene un PlanTrabajo asociado, the SGCA shall rechazar la solicitud de creación e informar que esa acción ya tiene un plan de trabajo
3. If la Accion referenciada no existe en el tenant activo, the SGCA shall rechazar la operación con error de recurso no encontrado
4. While la Accion tiene estado "verificado", the SGCA shall rechazar la creación o modificación del PlanTrabajo
5. The SGCA shall requerir que todo responsable asignado a una actividad pertenezca al mismo tenant que la acción

---

### Requirement 2: Gestión de Actividades
**Objective:** As admin, supervisor o responsable asignado a la actividad, I want gestionar las actividades del plan, so that pueda añadir, editar y eliminar actividades según evoluciona la ejecución

#### Acceptance Criteria
1. When un admin o supervisor añade una actividad al plan con descripción, responsable y fecha límite, the SGCA shall registrar la actividad con estado "pendiente" y recalcular el progreso del plan
2. The SGCA shall permitir al admin y supervisor editar la descripción, responsable y fecha límite de cualquier actividad del tenant
3. The SGCA shall permitir al responsable de una actividad editar únicamente la descripción de su propia actividad; no puede reasignar el responsable ni cambiar la fecha límite
4. When un admin o supervisor elimina una actividad, the SGCA shall eliminar la actividad con todas sus evidencias de S3 y recalcular el progreso del plan
5. If se intenta eliminar la única actividad del plan, the SGCA shall rechazar la operación e informar que el plan debe tener al menos una actividad
6. The SGCA shall garantizar que cada actividad tenga descripción no vacía, responsable válido del tenant, y fecha límite no en el pasado al momento de creación

---

### Requirement 3: Transiciones de Estado de Actividades
**Objective:** As responsable de la actividad, I want actualizar el estado de mi actividad según avanza la ejecución, so that el plan refleje el progreso real del trabajo

#### Acceptance Criteria
1. When el responsable de una actividad cambia su estado de "pendiente" a "en_proceso", the SGCA shall actualizar el estado y recalcular el progreso del plan
2. When el responsable de una actividad cambia su estado de "en_proceso" a "completada", the SGCA shall actualizar el estado y recalcular el progreso del plan
3. If un usuario intenta cambiar el estado de una actividad que no le está asignada y no tiene rol admin o supervisor, the SGCA shall rechazar la operación con error de permiso denegado
4. The SGCA shall permitir al admin y supervisor cambiar el estado de cualquier actividad del tenant a cualquier estado válido (pendiente/en_proceso/completada)
5. If se intenta cambiar el estado de una actividad a un valor no permitido, the SGCA shall rechazar la operación e informar los estados válidos

---

### Requirement 4: Subida y Gestión de Evidencias
**Objective:** As responsable de la actividad, I want subir archivos como evidencia de ejecución, so that el supervisor pueda verificar que la actividad fue realizada con evidencia concreta

#### Acceptance Criteria
1. When el responsable de una actividad sube un archivo válido (PDF, JPG, PNG, MP4, máximo 50 MB), the SGCA shall almacenarlo en S3/MinIO bajo la ruta `{tenant-slug}/evidencias/{accion_id}/{actividad_id}/{nombre_archivo}` y registrar la Evidencia con metadatos (nombre, tipo, tamaño, timestamp)
2. If el archivo supera 50 MB, the SGCA shall rechazar la subida e informar el límite máximo de tamaño
3. If el tipo de archivo no es PDF, JPG, PNG ni MP4, the SGCA shall rechazar la subida e informar los tipos aceptados
4. The SGCA shall permitir al admin y supervisor subir evidencias a cualquier actividad del tenant
5. When un admin o supervisor elimina una evidencia, the SGCA shall eliminar el archivo de S3/MinIO y el registro de la Evidencia
6. The SGCA shall permitir al responsable de la actividad eliminar únicamente las evidencias de sus propias actividades

---

### Requirement 5: Acceso Seguro a Evidencias
**Objective:** As usuario autorizado, I want acceder a las evidencias mediante URLs seguras y temporales, so that los archivos no estén expuestos públicamente en S3

#### Acceptance Criteria
1. When un usuario autorizado solicita la descarga de una evidencia, the SGCA shall generar una URL firmada de S3/MinIO con expiración de 1 hora y retornarla al cliente
2. The SGCA shall garantizar que ningún archivo de evidencia tenga acceso público directo en S3/MinIO
3. If la URL firmada ha expirado y el usuario intenta usarla, the SGCA shall rechazar el acceso (comportamiento estándar de S3/MinIO)
4. The SGCA shall requerir autenticación JWT válida antes de generar cualquier URL firmada
5. The SGCA shall garantizar que un usuario solo pueda obtener URLs firmadas de evidencias de su propio tenant

---

### Requirement 6: Progreso y Completitud del Plan
**Objective:** As supervisor o admin, I want ver el progreso del plan de trabajo en tiempo real, so that pueda evaluar el avance antes de aprobar el cierre de la acción

#### Acceptance Criteria
1. The SGCA shall calcular el progreso del plan como el porcentaje de actividades con estado "completada" sobre el total de actividades del plan, redondeado al entero más cercano
2. When cambia el estado de cualquier actividad del plan, the SGCA shall recalcular y actualizar el porcentaje de progreso inmediatamente
3. The SGCA shall exponer una operación interna que retorne si todas las actividades de un plan están en estado "completada", utilizable por AccionService para validar la transición "En proceso → Cerrado"
4. If el plan no tiene actividades, the SGCA shall reportar progreso 0%
5. The SGCA shall incluir el porcentaje de progreso en la respuesta del endpoint de detalle del PlanTrabajo

---

### Requirement 7: Control de Acceso por Rol
**Objective:** As operador de la plataforma, I want que cada rol tenga acceso apropiado al plan y sus actividades, so that los responsables ejecuten y los supervisores validen sin mezclar responsabilidades

#### Acceptance Criteria
1. The SGCA shall permitir al admin ver y gestionar todos los planes de trabajo del tenant activo
2. The SGCA shall permitir al supervisor ver todos los planes y actividades del tenant, editar cualquier actividad y cambiar cualquier estado
3. The SGCA shall permitir al responsable ver solo los planes de las acciones que le están asignadas y gestionar las actividades que le pertenecen
4. The SGCA shall permitir al verificador ver todos los planes y evidencias del tenant (solo lectura)
5. If un responsable intenta acceder al plan de una acción que no le está asignada, the SGCA shall rechazar el acceso con error 403
6. The SGCA shall garantizar que ningún dato de planes o evidencias de un tenant sea accesible desde otro tenant
