# Requirements Document

## Project Description (Input)
Después de registrar un incidente de seguridad en SGCA, las empresas necesitan gestionar formalmente las acciones de respuesta (correctivas, preventivas, de mejora), asignar responsables y hacer seguimiento del estado hasta que se verifique su eficacia. Sin trazabilidad formal de acciones y un historial de estados auditable, no es posible demostrar cumplimiento normativo ante una auditoría. La spec acciones implementa el ciclo de vida de acciones desde su creación vinculada a un Issue, hasta la transición por estados con validación de rol y una tabla de historial inmutable. Queda fuera: plan de trabajo con actividades (→ planes-trabajo), emails de notificación (→ notificaciones), reportes (→ reportes-dashboard), verificación de eficacia programada (→ verificacion-eficacia).

## Introducción
Acciones gestiona las acciones formales de respuesta (correctivas, preventivas y de mejora) generadas a partir de issues de seguridad industrial en SGCA. Cada acción tiene un responsable asignado, una fecha límite, una descripción del resultado esperado y transita por estados validados por rol: Abierto → En proceso → Cerrado → Verificado. El historial de cambios de estado es inmutable y sirve de evidencia auditable. Esta spec es la fuente de verdad del modelo Accion; las specs downstream (planes-trabajo, verificacion-eficacia, notificaciones) consumen este modelo sin modificarlo.

## Boundary Context
- **In scope**: Creación de acciones desde issues, tipos (correctiva/preventiva/mejora), asignación de responsable y fecha límite, máquina de estados con validación de rol por transición, historial de estados inmutable (HistorialEstado), listado y filtros por tenant, señal de cambio de estado para downstream, impacto en el issue de origen al crear la primera acción
- **Out of scope**: Plan de trabajo con actividades (→ planes-trabajo), subida de evidencias (→ planes-trabajo), emails de cambio de estado (→ notificaciones), verificación de eficacia programada (→ verificacion-eficacia), reportes y dashboard (→ reportes-dashboard)
- **Adjacent expectations**: planes-trabajo asume que el modelo Accion existe y crea PlanTrabajo con FK a Accion; verificacion-eficacia asume que puede programar verificaciones escuchando la señal de transición a "Cerrado"; notificaciones asume que puede escuchar señales de cambio de estado de Accion para enviar emails

## Requirements

### Requirement 1: Creación de Acciones desde Issues
**Objective:** As an admin o supervisor, I want crear una o más acciones formales de respuesta vinculadas a un issue de seguridad, so that quede registrada formalmente la decisión de respuesta de la empresa ante el evento reportado

#### Acceptance Criteria
1. When un admin o supervisor envía los datos de una nueva acción (tipo, descripción del resultado esperado, responsable, fecha límite) vinculada a un issue existente en el tenant activo, the SGCA shall crear la acción con estado inicial "Abierto"
2. The SGCA shall soportar exactamente tres tipos de acción: correctiva, preventiva y de mejora
3. The SGCA shall requerir como campos obligatorios: tipo, descripción del resultado esperado, responsable asignado y fecha límite
4. If el responsable indicado no pertenece al tenant activo, the SGCA shall rechazar la creación e informar que el usuario no existe en el tenant
5. The SGCA shall permitir crear múltiples acciones vinculadas al mismo issue sin restricción de cantidad
6. When se crea la primera acción vinculada a un issue cuyo estado actual es "En Análisis", the SGCA shall disparar automáticamente la transición del issue al estado "Acciones Generadas"
7. If un usuario con rol responsable o verificador intenta crear una acción, the SGCA shall rechazar la operación con un error de permisos

---

### Requirement 2: Máquina de Estados con Validación de Rol
**Objective:** As a usuario del sistema, I want que cada transición de estado de una acción valide el rol del solicitante, so that solo el rol autorizado pueda avanzar la acción en cada etapa del ciclo de vida

#### Acceptance Criteria
1. The SGCA shall mantener la siguiente secuencia de estados unidireccional para las acciones: Abierto → En proceso → Cerrado → Verificado
2. When el responsable asignado a la acción solicita la transición de "Abierto" a "En proceso", the SGCA shall ejecutar la transición y registrarla en el historial de estados
3. If un usuario cuyo rol no es responsable asignado ni admin solicita la transición de "Abierto" a "En proceso", the SGCA shall rechazar la operación e informar el rol requerido
4. When un usuario con rol supervisor solicita la transición de "En proceso" a "Cerrado", the SGCA shall ejecutar la transición y registrarla en el historial de estados
5. If un usuario cuyo rol no es supervisor ni admin solicita la transición de "En proceso" a "Cerrado", the SGCA shall rechazar la operación e informar el rol requerido
6. When un usuario con rol verificador solicita la transición de "Cerrado" a "Verificado", the SGCA shall ejecutar la transición y registrarla en el historial de estados
7. If un usuario cuyo rol no es verificador ni admin solicita la transición de "Cerrado" a "Verificado", the SGCA shall rechazar la operación e informar el rol requerido
8. If un usuario solicita una transición de estado que no está definida en la secuencia válida, the SGCA shall rechazar la operación e informar que la transición no es válida
9. The SGCA shall permitir que un usuario con rol admin realice cualquier transición de estado en cualquier acción del tenant

---

### Requirement 3: Historial de Estados para Auditoría
**Objective:** As system admin o auditor externo, I want que cada cambio de estado de una acción quede registrado de forma inmutable, so that pueda demostrarse ante una auditoría quién realizó cada cambio de estado y cuándo

#### Acceptance Criteria
1. When se ejecuta cualquier transición de estado de una acción, the SGCA shall registrar automáticamente: el usuario que realizó la transición, el estado anterior, el estado nuevo y la fecha y hora exacta de la transición
2. The SGCA shall permitir que el usuario que realiza la transición agregue un comentario opcional al registro del historial
3. The SGCA shall garantizar que ningún usuario de ningún rol pueda editar ni eliminar registros del historial de estados
4. The SGCA shall mostrar el historial completo de estados de una acción a usuarios con rol admin o supervisor al consultar el detalle de la acción
5. The SGCA shall garantizar que el historial de estados de una acción pertenece exclusivamente al tenant activo y no es accesible desde otro tenant

---

### Requirement 4: Visibilidad y Control de Acceso por Rol
**Objective:** As usuario del sistema, I want ver únicamente las acciones que mi rol me permite ver y ejecutar únicamente las operaciones que estoy autorizado a hacer, so that la información de la empresa esté protegida por control de acceso granular

#### Acceptance Criteria
1. While un usuario con rol admin está autenticado, the SGCA shall permitirle ver, crear, editar y gestionar el estado de todas las acciones del tenant activo
2. While un usuario con rol responsable está autenticado, the SGCA shall permitirle ver únicamente las acciones donde es el responsable asignado
3. While un usuario con rol supervisor está autenticado, the SGCA shall permitirle ver todas las acciones del tenant y gestionar la transición de "En proceso" a "Cerrado"
4. While un usuario con rol verificador está autenticado, the SGCA shall permitirle ver todas las acciones del tenant y gestionar la transición de "Cerrado" a "Verificado"
5. If un usuario intenta acceder o modificar una acción fuera del alcance de su rol, the SGCA shall rechazar la operación con un error de permisos

---

### Requirement 5: Listado y Filtros
**Objective:** As admin o supervisor, I want listar y filtrar acciones por múltiples criterios, so that pueda hacer seguimiento eficiente del estado general de las acciones del tenant

#### Acceptance Criteria
1. The SGCA shall proveer un listado paginado de acciones mostrando: tipo, resumen del resultado esperado, responsable asignado, estado actual, fecha límite e issue de origen
2. The SGCA shall soportar filtros por: estado, tipo de acción, responsable asignado, rango de fecha de creación y rango de fecha límite
3. The SGCA shall soportar ordenamiento por: fecha de creación, fecha límite y estado
4. The SGCA shall aplicar las reglas de visibilidad por rol al listado (el responsable solo ve sus propias acciones)
5. The SGCA shall garantizar que el listado únicamente incluye acciones del tenant activo

---

### Requirement 6: Edición de Acciones
**Objective:** As admin, I want poder editar los datos de una acción después de crearla, so that pueda corregir información o actualizar responsables y plazos cuando cambien las circunstancias

#### Acceptance Criteria
1. When un admin edita los campos de una acción (tipo, descripción del resultado esperado, responsable, fecha límite), the SGCA shall actualizar la acción preservando su estado actual y su historial de estados existente
2. If se intenta editar una acción que tiene estado "Verificado", the SGCA shall rechazar la modificación e informar que las acciones verificadas no pueden ser modificadas
3. The SGCA shall restringir la edición de los campos de una acción únicamente al rol admin
