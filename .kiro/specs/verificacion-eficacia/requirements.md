# Requirements Document

## Project Description (Input)
Las empresas industriales necesitan verificar que las acciones correctivas, preventivas y de mejora realmente funcionaron a largo plazo. Actualmente (greenfield), el sistema registra acciones con estado "Cerrado" pero no existe ningún mecanismo para programar ni registrar verificaciones de eficacia futuras. Se necesita que al cerrar una acción el sistema programe automáticamente verificaciones a 6, 12 y 24 meses; que Celery Beat detecte las verificaciones con fecha_programada == hoy y emita un evento para que notificaciones envíe el email al verificador; que el verificador registre el resultado (eficaz/no_eficaz) con notas; y que si el resultado es no_eficaz se pueda generar un nuevo Issue vinculado. El scope excluye el envío del email (→ notificaciones), el upload de evidencias de verificación (→ planes-trabajo) y la transición a estado "Verificado" de la Accion (→ acciones).

## Introducción
SGCA Verificación de Eficacia gestiona el seguimiento a largo plazo de las acciones correctivas y preventivas, programando automáticamente verificaciones periódicas y registrando sus resultados. Esta especificación cubre la creación automática de verificaciones al cerrar una acción, la detección de fechas de verificación, el registro de resultados por el verificador y el flujo de reincidencia. La emisión del email de notificación es responsabilidad de la especificación notificaciones.

## Boundary Context
- **In scope**: Modelo VerificacionEficacia, programación automática de 3 verificaciones al cerrar una Accion (+6m/+12m/+24m), tarea Celery Beat de detección diaria, señal verificacion_proxima_detectada, endpoint de registro de resultado (solo verificador), flujo de creación de Issue por reincidencia, historial de verificaciones por acción, aislamiento por tenant
- **Out of scope**: Envío del email de notificación (→ notificaciones consume la señal verificacion_proxima_detectada), upload de archivos de evidencia de verificación (→ planes-trabajo), transición a estado "Verificado" de la Accion (→ acciones)
- **Adjacent expectations**: notificaciones asume que verificacion-eficacia emite la señal verificacion_proxima_detectada con los datos del verificador y la acción antes de que notificaciones envíe el email; acciones asume que verificacion-eficacia registra su handler en apps.ready() para escuchar accion_estado_cambiado sin modificar el modelo Accion

## Requirements

### Requirement 1: Programación automática de verificaciones al cerrar una acción
**Objective:** As a supervisor, I want que el sistema programe automáticamente las verificaciones de eficacia cuando cierro una acción, so that el seguimiento a largo plazo ocurra sin intervención manual y quede trazabilidad para auditorías

#### Acceptance Criteria
1. When una Accion cambia a estado "cerrado" (señal accion_estado_cambiado con estado_nuevo='cerrado'), the SGCA shall crear automáticamente 3 registros de VerificacionEficacia con fechas programadas: fecha_cierre + 6 meses, fecha_cierre + 12 meses y fecha_cierre + 24 meses
2. When se crean los registros de verificación, the SGCA shall asignarles resultado "pendiente" y no asignar verificador hasta que un verificador registre el resultado
3. If la Accion ya tiene un registro de VerificacionEficacia con la misma fecha_programada (caso de re-cierre tras reapertura), the SGCA shall no crear registros duplicados para esa fecha y mantener el registro existente
4. When una Accion es eliminada del sistema, the SGCA shall eliminar en cascada todos sus registros de VerificacionEficacia asociados
5. The SGCA shall garantizar que la creación de las 3 verificaciones ocurra de forma atómica dentro de la misma transacción que procesa la señal

---

### Requirement 2: Detección diaria de verificaciones próximas
**Objective:** As a verificador, I want recibir notificación automática cuando llega la fecha programada de una verificación, so that pueda realizar la verificación de eficacia oportunamente sin depender de revisión manual del calendario

#### Acceptance Criteria
1. The SGCA shall ejecutar automáticamente una tarea diaria mediante Celery Beat para identificar verificaciones pendientes cuya fecha_programada sea igual a la fecha actual
2. When la tarea diaria detecta registros de VerificacionEficacia con fecha_programada == hoy y resultado == 'pendiente', the SGCA shall emitir la señal verificacion_proxima_detectada con los datos de la verificación y la acción correspondiente para que notificaciones procese el envío del email
3. If no existen verificaciones con fecha_programada == hoy, the SGCA shall concluir la tarea sin emitir señales ni registrar errores
4. The SGCA shall procesar verificaciones de todos los tenants activos durante la ejecución de la tarea diaria sin mezclar datos entre tenants
5. The SGCA shall garantizar que la tarea diaria sea idempotente: ejecutarla múltiples veces el mismo día no debe emitir señales duplicadas para la misma verificación

---

### Requirement 3: Registro de resultado de verificación
**Objective:** As a verificador, I want registrar formalmente si una acción fue eficaz o no en la fecha de verificación, so that quede constancia auditable de la efectividad real de las acciones correctivas a largo plazo

#### Acceptance Criteria
1. When un verificador envía el resultado de una verificación, the SGCA shall actualizar el registro con resultado (eficaz o no_eficaz), fecha_real de la verificación y notas del verificador
2. The SGCA shall requerir el campo resultado como obligatorio al registrar; el campo notas es opcional
3. The SGCA shall permitir únicamente a usuarios con rol verificador registrar el resultado de una verificación
4. If un usuario con rol distinto a verificador intenta registrar el resultado de una verificación, the SGCA shall rechazar la operación con un error 403
5. If una verificación ya tiene resultado registrado (resultado != 'pendiente'), the SGCA shall rechazar un segundo intento de registro con un error 400 y un mensaje que indique que la verificación ya fue completada

---

### Requirement 4: Creación de nuevo issue cuando la verificación es no eficaz
**Objective:** As a verificador, I want poder crear un nuevo issue de reincidencia cuando una acción no fue eficaz, so that el problema recurrente entre al ciclo de gestión de acciones nuevamente con trazabilidad hacia la acción original

#### Acceptance Criteria
1. When el verificador registra resultado "no_eficaz" y solicita crear un issue de reincidencia, the SGCA shall crear un nuevo Issue en el tenant activo vinculado a la Accion original mediante el campo accion_origen
2. When se crea el Issue de reincidencia, the SGCA shall inicializarlo con estado "abierto" y tipo "incidente" y dejarlo disponible para gestión completa en el módulo de issues
3. If el verificador registra resultado "no_eficaz" pero no solicita crear un issue de reincidencia, the SGCA shall completar el registro del resultado sin requerir la creación del issue
4. The SGCA shall vincular el registro de VerificacionEficacia con el Issue de reincidencia creado para mantener la trazabilidad completa del ciclo

---

### Requirement 5: Consulta de historial de verificaciones por acción
**Objective:** As an admin, I want ver el historial completo de verificaciones de cualquier acción, so that pueda supervisar la eficacia a largo plazo y preparar evidencia para auditorías de cumplimiento normativo

#### Acceptance Criteria
1. The SGCA shall proveer un endpoint que retorne todos los registros de VerificacionEficacia asociados a una Accion específica, ordenados por fecha_programada ascendente
2. The SGCA shall incluir en cada registro del historial: fecha_programada, fecha_real, resultado, nombre del verificador (si aplica) y notas
3. The SGCA shall permitir a los roles admin y supervisor consultar el historial de verificaciones de cualquier acción del tenant activo
4. If un usuario con rol responsable o verificador intenta consultar el historial de verificaciones, the SGCA shall retornar 403

---

### Requirement 6: Aislamiento de datos por tenant
**Objective:** As an operador de la plataforma, I want que los datos de verificación de eficacia estén completamente aislados por tenant, so that ninguna empresa pueda acceder a los datos de verificación de otra empresa bajo ninguna circunstancia

#### Acceptance Criteria
1. The SGCA shall garantizar que los registros de VerificacionEficacia solo sean accesibles desde el schema del tenant al que pertenecen
2. The SGCA shall garantizar que la tarea diaria de Celery Beat procese cada tenant de forma aislada sin que los datos de un tenant contaminen el procesamiento de otro
3. If un request intenta acceder a un registro de VerificacionEficacia que no pertenece al tenant activo, the SGCA shall retornar 404
