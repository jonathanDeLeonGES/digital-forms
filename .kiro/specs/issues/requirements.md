# Requirements Document

## Project Description (Input)
Las empresas industriales en Guatemala y Centroamérica no tienen forma estructurada de registrar eventos de seguridad (incidentes, casi incidentes, reuniones de seguridad) y analizar sus causas raíz. Los incidentes se registran en Excel o papel sin trazabilidad ni auditoría. Con Wave 1 completa (tenants y autenticación RBAC operativos), se necesita que cualquier usuario autenticado pueda registrar eventos de seguridad, capturar el análisis de causa raíz mediante Diagrama de Ishikawa (6 categorías fijas), gestionar el ciclo de vida del issue (Abierto → En Análisis → Acciones Generadas → Cerrado), y controlar la visibilidad por rol. Queda fuera: generación de acciones desde el issue (→ acciones), adjuntos (→ planes-trabajo), reportes PDF (→ reportes-dashboard), notificaciones (→ notificaciones).

## Introducción
El módulo Issues del SGCA permite registrar y analizar eventos de seguridad industrial dentro de cada tenant. Cada issue captura el evento con sus datos básicos y opcionalmente su análisis de causa raíz mediante el Diagrama de Ishikawa. Los issues tienen un ciclo de vida de cuatro estados y visibilidad diferenciada por rol.

## Boundary Context
- **In scope**: Registro de issues (tipo/título/descripción/fecha/área/gravedad), Diagrama de Ishikawa (6 categorías fijas + causas + subcausas), máquina de estados del issue, permisos por rol, listado paginado con filtros, aislamiento multi-tenant
- **Out of scope**: Creación de acciones correctivas desde el issue (→ acciones), subida de archivos adjuntos (→ planes-trabajo), generación de PDF del análisis (→ reportes-dashboard), notificaciones por email al crear o actualizar un issue (→ notificaciones)
- **Adjacent expectations**: La spec `acciones` asume que el modelo Issue existe con sus campos y estados definidos, y que expone un FK estable para vincular acciones. La spec `acciones` puede disparar la transición al estado "Acciones Generadas" vía señal de Django.

## Requirements

### Requirement 1: Registro de Evento de Seguridad
**Objective:** As a usuario autenticado, I want registrar un evento de seguridad con sus datos básicos, so that quede trazabilidad formal del evento con fecha, tipo, área y gravedad en el sistema.

#### Acceptance Criteria
1. When un usuario autenticado envía tipo (incidente/casi incidente/reunión de seguridad), título, descripción, fecha del evento, área afectada y gravedad, the SGCA shall crear el Issue con estado inicial "Abierto" y asignar como reportado_por al usuario autenticado.
2. If alguno de los campos obligatorios (tipo, título, descripción, fecha del evento, área, gravedad) está ausente o vacío, the SGCA shall rechazar la solicitud e indicar el campo faltante en la respuesta de error.
3. The SGCA shall permitir que un Issue exista sin Diagrama de Ishikawa asociado (el análisis es opcional).
4. The SGCA shall permitir que un Issue exista sin acciones generadas (las acciones son opcionales).
5. When un Issue es creado exitosamente, the SGCA shall retornar el Issue completo con su identificador único y timestamp de creación.

---

### Requirement 2: Análisis de Causa Raíz — Diagrama de Ishikawa
**Objective:** As a usuario autenticado, I want capturar el análisis de causa raíz usando el Diagrama de Ishikawa, so that las causas del evento queden documentadas de forma estructurada y auditable.

#### Acceptance Criteria
1. When un usuario solicita el Diagrama de Ishikawa de un Issue, the SGCA shall proveer una estructura con exactamente 6 categorías fijas: Método, Máquina, Material, Mano de Obra, Medición, Medio Ambiente.
2. When un usuario agrega una causa a una categoría del Ishikawa, the SGCA shall crear la causa vinculada a esa categoría del Issue.
3. When un usuario agrega una subcausa a una causa existente, the SGCA shall crear la subcausa vinculada a esa causa.
4. The SGCA shall permitir guardar un Diagrama de Ishikawa parcial donde no todas las categorías tengan causas registradas.
5. When un usuario actualiza el Diagrama de Ishikawa, the SGCA shall preservar las causas y subcausas no incluidas en la actualización.
6. When un usuario elimina una causa, the SGCA shall eliminar también todas sus subcausas asociadas.

---

### Requirement 3: Ciclo de Vida del Issue
**Objective:** As a usuario con rol autorizado, I want gestionar el estado del issue a través de su ciclo de vida, so that el progreso desde el registro hasta el cierre sea trazable y auditable.

#### Acceptance Criteria
1. The SGCA shall soportar los siguientes estados de Issue en orden: Abierto, En Análisis, Acciones Generadas, Cerrado.
2. When un usuario con rol admin o supervisor solicita una transición de estado válida, the SGCA shall actualizar el estado del Issue.
3. When un usuario con cualquier rol solicita la transición Abierto → En Análisis, the SGCA shall permitir la transición.
4. If el estado de destino solicitado no es una transición válida desde el estado actual, the SGCA shall rechazar la solicitud e informar las transiciones válidas disponibles.
5. When el estado de un Issue cambia, the SGCA shall registrar la transición con el usuario que la realizó y el timestamp.
6. The SGCA shall exponer el historial de transiciones de estado de un Issue a usuarios con rol admin o supervisor.

---

### Requirement 4: Control de Acceso por Rol
**Objective:** As administrador del tenant, I want que la visibilidad y las operaciones sobre los issues estén controladas por rol, so that cada usuario acceda solo a lo que le corresponde según su responsabilidad.

#### Acceptance Criteria
1. While un usuario con rol admin o supervisor está autenticado, the SGCA shall permitirles ver, crear, actualizar y gestionar todos los Issues del tenant.
2. While un usuario con rol responsable está autenticado, the SGCA shall permitirles crear nuevos Issues y ver únicamente los Issues que ellos reportaron (reportado_por = usuario actual).
3. While un usuario con rol verificador está autenticado, the SGCA shall permitirles ver todos los Issues del tenant en modo solo lectura, sin poder crear, modificar ni eliminar.
4. If un usuario autenticado intenta realizar una operación no permitida por su rol, the SGCA shall rechazar la solicitud con código 403 Forbidden.
5. The SGCA shall impedir que cualquier usuario acceda a Issues de un tenant diferente al suyo.

---

### Requirement 5: Listado, Búsqueda y Filtros
**Objective:** As usuario autenticado, I want obtener listas paginadas de Issues con filtros aplicables, so that pueda encontrar rápidamente los eventos relevantes sin descargar todos los registros.

#### Acceptance Criteria
1. The SGCA shall retornar los Issues accesibles al usuario autenticado en forma paginada, con un tamaño de página configurable.
2. When un usuario aplica filtro por tipo (incidente/casi incidente/reunión), the SGCA shall retornar únicamente Issues del tipo especificado.
3. When un usuario aplica filtro por estado (Abierto/En Análisis/Acciones Generadas/Cerrado), the SGCA shall retornar únicamente Issues en ese estado.
4. When un usuario aplica filtro por gravedad o área, the SGCA shall retornar únicamente Issues que coincidan con los valores especificados.
5. When un usuario aplica filtro por rango de fecha del evento, the SGCA shall retornar únicamente Issues cuya fecha_evento esté dentro del rango.
6. The SGCA shall garantizar que la respuesta de listado nunca incluya Issues de otro tenant, independientemente de los filtros aplicados.

---

### Requirement 6: Aislamiento Multi-Tenant
**Objective:** As operador de la plataforma, I want que los Issues de cada empresa estén completamente aislados, so that ninguna empresa pueda ver ni afectar los datos de otra empresa.

#### Acceptance Criteria
1. When un Issue es creado, the SGCA shall asociarlo exclusivamente con el tenant activo en ese momento.
2. The SGCA shall garantizar que cualquier operación sobre Issues (crear, leer, actualizar, eliminar) opere únicamente sobre los Issues del tenant identificado por el subdominio del request.
3. The SGCA shall garantizar que un Issue de un tenant no sea accesible desde la sesión de otro tenant, aun si el identificador del Issue es conocido.
