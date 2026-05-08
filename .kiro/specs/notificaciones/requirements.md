# Requirements Document

## Project Description (Input)
Los responsables olvidan sus deadlines, los supervisores no saben cuándo deben revisar acciones y el admin no tiene visibilidad del estado global. Sin notificaciones automáticas, el sistema de gestión de acciones de seguridad industrial pierde efectividad operativa. Se necesita un sistema de notificaciones por email que: (1) alerte a responsables cuando se les asigna una acción o cuando sus actividades están próximas a vencer (3 días, 1 día, vencido); (2) notifique a supervisores cuando hay acciones listas para revisión; (3) notifique a verificadores cuando hay verificaciones de eficacia programadas para hoy; (4) envíe un resumen semanal al admin del estado general. El sistema usa Celery + Redis para tareas asíncronas, SendGrid para envío de emails, y Django Signals para detectar eventos de los módulos upstream (acciones, verificacion-eficacia). Queda fuera: notificaciones in-app, SMS, programación de verificaciones de eficacia (eso es responsabilidad de verificacion-eficacia).

## Introducción
SGCA Notificaciones es el sistema centralizado de despacho de emails del SGCA. Escucha señales de otros módulos (acciones, verificacion-eficacia) y ejecuta tareas Celery Beat programadas para enviar todos los emails del sistema vía SendGrid. Esta especificación cubre exclusivamente la entrega de emails; la lógica de negocio que determina cuándo ocurren los eventos (cambios de estado de acciones, detección de verificaciones próximas) es responsabilidad de las specs upstream correspondientes.

## Boundary Context
- **In scope**: Envío de emails para: asignación de acción, deadlines de actividades (3d/1d/vencido), acción lista para revisión de supervisor, verificación de eficacia próxima, resumen semanal al admin. Tareas Celery async y Celery Beat schedules. Plantillas HTML de email. Configuración de preferencias de notificación por usuario. Idempotencia de alertas de deadline. Log de alertas enviadas para evitar duplicados.
- **Out of scope**: Notificaciones in-app o push, SMS, Slack/Teams. Programación de verificaciones de eficacia (→ verificacion-eficacia). Generación de reportes en background (→ reportes-dashboard). Historial detallado de emails enviados (nice-to-have futuro).
- **Adjacent expectations**: Los módulos acciones y verificacion-eficacia emiten las señales `accion_estado_cambiado` y `verificacion_proxima_detectada` respectivamente. Este módulo registra handlers de esas señales en su propio `apps.py`. Los handlers son fire-and-forget: si fallan no deben propagar el error upstream. El módulo planes-trabajo expone `Actividad.fecha_limite` como dato de lectura directa para el deadline scanning.

## Requirements

### Requirement 1: Notificación de Asignación de Acción
**Objective:** As a responsable de una acción, I want recibir un email cuando se me asigna una acción, so that pueda comenzar a trabajar en ella inmediatamente sin necesidad de monitorear el sistema constantemente

#### Acceptance Criteria
1. When una Accion transita al estado "en_proceso" (señal `accion_estado_cambiado` con `estado_nuevo='en_proceso'`), the SGCA shall enviar un email al responsable asignado con los detalles de la acción (tipo, resultado esperado, fecha límite, nombre del issue origen).
2. If el responsable tiene la notificación de asignación de acción desactivada en su configuración, the SGCA shall omitir el envío del email para ese usuario.
3. If el responsable tiene su cuenta desactivada (`is_active=False`), the SGCA shall omitir el envío del email.
4. The SGCA shall procesar el envío del email de asignación de forma asíncrona mediante una tarea Celery, sin bloquear la transición de estado de la acción.

---

### Requirement 2: Alertas de Deadline de Actividades
**Objective:** As a responsable de una actividad, I want recibir alertas por email antes de que venza el deadline de mis actividades pendientes, so that pueda tomar acción a tiempo y no incumplir fechas límite

#### Acceptance Criteria
1. When el sistema detecta que una Actividad tiene `fecha_limite` en exactamente 3 días calendario y su estado no es "completada", the SGCA shall enviar un email de alerta al responsable de la actividad.
2. When el sistema detecta que una Actividad tiene `fecha_limite` en exactamente 1 día calendario y su estado no es "completada", the SGCA shall enviar un email de alerta al responsable de la actividad.
3. When el sistema detecta que una Actividad tiene `fecha_limite` igual a la fecha actual o anterior y su estado no es "completada", the SGCA shall enviar un email de alerta de vencimiento al responsable de la actividad.
4. The SGCA shall ejecutar la detección de deadlines próximos automáticamente una vez al día mediante una tarea Celery Beat.
5. If el responsable de una actividad tiene desactivado el tipo de alerta de deadline correspondiente en su configuración, the SGCA shall omitir el envío del email para esa actividad.
6. If el responsable de una actividad tiene su cuenta desactivada, the SGCA shall omitir el envío del email para esa actividad.
7. The SGCA shall garantizar que cada tipo de alerta de deadline (3d, 1d, vencido) para una misma actividad no se envíe más de una vez por día calendario.

---

### Requirement 3: Notificación de Acción Lista para Revisión
**Objective:** As supervisor, I want recibir un email cuando una acción pasa a estado "cerrado", so that pueda revisarla y aprobar su cierre oportunamente

#### Acceptance Criteria
1. When una Accion transita al estado "cerrado" (señal `accion_estado_cambiado` con `estado_nuevo='cerrado'`), the SGCA shall enviar un email a todos los usuarios con rol supervisor activos del tenant con los detalles de la acción.
2. If no hay usuarios con rol supervisor activos en el tenant, the SGCA shall omitir el envío sin generar error.
3. If un supervisor tiene desactivada la notificación de acción lista para revisión, the SGCA shall omitir el envío para ese supervisor.
4. The SGCA shall procesar el envío de manera asíncrona mediante una tarea Celery.

---

### Requirement 4: Notificación de Verificación de Eficacia Próxima
**Objective:** As verificador, I want recibir un email cuando hay una verificación de eficacia programada para hoy, so that pueda registrar el resultado de la verificación en el momento adecuado

#### Acceptance Criteria
1. When el sistema recibe la señal `verificacion_proxima_detectada` con una VerificacionEficacia cuya `fecha_programada` es hoy y `resultado='pendiente'`, the SGCA shall enviar un email a todos los usuarios con rol verificador activos del tenant con los detalles de la acción a verificar.
2. If no hay usuarios con rol verificador activos en el tenant, the SGCA shall omitir el envío sin generar error.
3. If un verificador tiene desactivada la notificación de verificación próxima, the SGCA shall omitir el envío para ese verificador.
4. The SGCA shall procesar el envío de manera asíncrona tras recibir el evento de verificación próxima.

---

### Requirement 5: Resumen Semanal al Admin
**Objective:** As admin del tenant, I want recibir un resumen semanal por email del estado de las acciones, so that pueda tener visibilidad global de la seguridad sin acceder al sistema constantemente

#### Acceptance Criteria
1. The SGCA shall enviar automáticamente un resumen semanal a todos los usuarios con rol admin activos de cada tenant mediante una tarea Celery Beat.
2. The SGCA shall incluir en el resumen: total de acciones por estado (abierto, en_proceso, cerrado, verificado), número de actividades con deadline vencido y estado no completado, número de acciones en estado "cerrado" pendientes de cierre formal.
3. If no hay usuarios con rol admin activos en el tenant, the SGCA shall omitir el envío para ese tenant.
4. If un admin tiene desactivada la notificación de resumen semanal, the SGCA shall omitir el envío para ese admin.

---

### Requirement 6: Configuración de Preferencias de Notificación
**Objective:** As usuario del sistema, I want poder configurar qué tipos de notificaciones recibo, so that pueda controlar el volumen de emails sin perder las que considero importantes

#### Acceptance Criteria
1. The SGCA shall permitir a cada usuario activar o desactivar de forma independiente cada tipo de notificación: asignación de acción, alerta de deadline 3d, alerta de deadline 1d, alerta de deadline vencido, acción lista para revisión, verificación próxima, resumen semanal.
2. When un usuario no tiene configuración de notificaciones registrada, the SGCA shall aplicar los valores predeterminados con todos los tipos de notificación activos.
3. The SGCA shall proveer un endpoint REST para que el usuario consulte y actualice sus preferencias de notificación.
4. The SGCA shall respetar las preferencias de notificación de cada usuario en todos los envíos de email.

---

### Requirement 7: Fiabilidad y Aislamiento de Fallos
**Objective:** As operador de la plataforma, I want que el sistema de notificaciones sea confiable y no afecte el funcionamiento principal del sistema, so that un fallo en el envío de emails no impacte las operaciones de los usuarios

#### Acceptance Criteria
1. The SGCA shall procesar todos los envíos de email de forma asíncrona a través de Celery, sin bloquear operaciones de negocio.
2. If el servicio SendGrid falla al enviar un mensaje, the SGCA shall reintentar el envío hasta 3 veces con espera exponencial.
3. If un handler de señal de notificaciones lanza una excepción, the SGCA shall capturarla y registrarla en el log sin propagar el error a la operación que emitió la señal.
4. The SGCA shall omitir el envío de emails a usuarios con `is_active=False` en todos los tipos de notificación.
5. The SGCA shall garantizar que las tareas Celery de envío de email sean idempotentes mediante el uso de task IDs únicos basados en el tipo de notificación, el destinatario y la fecha.
