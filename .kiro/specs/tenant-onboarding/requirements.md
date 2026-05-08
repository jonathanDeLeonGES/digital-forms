# Requirements Document

## Project Description (Input)
Las empresas industriales en Guatemala y Centroamérica no tienen forma estructurada de registrarse en SGCA y obtener su espacio aislado de trabajo. Actualmente el sistema no existe (proyecto greenfield) y django-tenants está definido en el stack pero no implementado. Se necesita que una empresa pueda registrarse y obtener su subdominio/tenant con un período de prueba de 14 días, que el system admin pueda gestionar planes (Trial/Enterprise) y licencias sin autoservicio de pagos, y que los tenants con trial vencido pierdan acceso sin perder sus datos. El scope incluye: registro de tenant, creación automática de espacio de datos aislado, modelos Plan y Subscription, middleware de identificación por subdominio, bloqueo de acceso para trials vencidos, y panel de system admin. Queda fuera: autenticación de usuarios (→ auth-rbac), pagos/Stripe y auto-upgrades.

## Introducción
SGCA Tenant Onboarding gestiona el registro de nuevas empresas en la plataforma, la provisión de su espacio de datos aislado, la gestión de planes de suscripción (Trial/Enterprise) y el acceso controlado por subdominio. Esta especificación cubre únicamente la incorporación del tenant y la gestión de planes; la autenticación de usuarios dentro del tenant la gestiona la especificación auth-rbac.

## Boundary Context
- **In scope**: Registro de tenant, aprovisionamiento de espacio de datos aislado, planes Trial y Enterprise, middleware de identificación por subdominio, bloqueo de acceso a trials vencidos, panel de system admin para gestión de tenants y licencias
- **Out of scope**: Autenticación de usuarios (→ auth-rbac), pagos y facturación (fuera del MVP), upgrades automáticos, gestión de usuarios dentro del tenant (→ auth-rbac)
- **Adjacent expectations**: El sistema auth-rbac asume que el espacio de datos del tenant ya existe y que el middleware de subdominio inyecta el tenant activo en cada request antes de que auth-rbac procese la autenticación

## Requirements

### Requirement 1: Registro de Tenant
**Objective:** As a representante de empresa, I want registrar mi empresa en SGCA proporcionando datos básicos, so that obtenga un espacio de trabajo aislado con subdominio propio y período de prueba activo de 14 días

#### Acceptance Criteria
1. When un representante envía nombre de empresa, subdominio y email del administrador, the SGCA shall crear un nuevo tenant con espacio de datos aislado y activar automáticamente un período de prueba de 14 días
2. If el subdominio solicitado ya está registrado en el sistema, the SGCA shall rechazar el registro e informar que el subdominio no está disponible
3. If el subdominio contiene caracteres no permitidos (solo se permiten letras minúsculas, dígitos y guiones), the SGCA shall rechazar el registro e informar el formato requerido
4. When el registro es exitoso, the SGCA shall inicializar automáticamente la estructura de datos completa del tenant sin requerir intervención manual
5. The SGCA shall requerir nombre de empresa y email del administrador como campos obligatorios para completar el registro

---

### Requirement 2: Aislamiento de Datos por Tenant
**Objective:** As operador de la plataforma, I want que cada tenant tenga un espacio de datos completamente aislado, so that ninguna empresa pueda ver o acceder a los datos de otra empresa bajo ninguna circunstancia

#### Acceptance Criteria
1. When un nuevo tenant es registrado, the SGCA shall preparar el espacio de datos aislado del tenant antes de retornar confirmación de registro exitoso
2. The SGCA shall garantizar que ningún dato de un tenant sea accesible desde la sesión de otro tenant
3. If la preparación del espacio de datos falla durante el registro, the SGCA shall revertir el registro completo y no dejar recursos huérfanos en el sistema
4. The SGCA shall inicializar la estructura de datos necesaria para el funcionamiento del tenant durante el aprovisionamiento

---

### Requirement 3: Gestión de Planes de Suscripción
**Objective:** As system admin, I want gestionar los planes Trial y Enterprise de cada tenant, so that pueda controlar el acceso y las licencias sin depender de procesos de pago automáticos

#### Acceptance Criteria
1. The SGCA shall soportar dos planes: Trial (con fecha de vencimiento, por defecto 14 días desde el registro) y Enterprise (acceso sin límite de tiempo con número máximo de usuarios activos definido)
2. When el system admin cambia un tenant de Trial a Enterprise y especifica el número de licencias, the SGCA shall activar el plan Enterprise inmediatamente
3. When el system admin extiende la fecha de vencimiento de un tenant Trial, the SGCA shall actualizar la fecha y restaurar el acceso si estaba bloqueado por vencimiento
4. When el system admin asigna el número de licencias a un tenant Enterprise, the SGCA shall hacer cumplir ese límite rechazando la activación de usuarios adicionales que lo superen
5. If el system admin intenta asignar cero licencias a un tenant Enterprise, the SGCA shall rechazar la operación y solicitar un número de licencias mayor a cero

---

### Requirement 4: Identificación de Tenant por Subdominio
**Objective:** As usuario de cualquier tenant, I want que el sistema me identifique automáticamente por el subdominio al que accedo, so that los datos que veo correspondan exclusivamente a mi empresa

#### Acceptance Criteria
1. While procesando cualquier request entrante, the SGCA shall identificar el tenant activo a partir del subdominio de la URL y dejarlo disponible para el resto del procesamiento del request
2. If el subdominio de la URL no corresponde a ningún tenant registrado, the SGCA shall rechazar el request con un mensaje que indica que el subdominio no existe
3. The SGCA shall garantizar que todas las operaciones de datos del request correspondan exclusivamente al tenant identificado por el subdominio

---

### Requirement 5: Bloqueo de Acceso a Trials Vencidos
**Objective:** As system admin, I want que los tenants con trial vencido no puedan acceder a la aplicación, so that el sistema no sea usado indefinidamente sin una suscripción activa

#### Acceptance Criteria
1. If un tenant Trial intenta acceder a la aplicación después de su fecha de vencimiento, the SGCA shall bloquear el acceso e informar al usuario que el período de prueba ha finalizado y que debe contactar al administrador
2. The SGCA shall preservar todos los datos del tenant cuando el acceso está bloqueado por vencimiento del trial
3. When el system admin extiende la fecha de vencimiento o activa el plan Enterprise para un tenant bloqueado, the SGCA shall restaurar el acceso inmediatamente sin requerir intervención adicional
4. While un tenant Trial está dentro de su período de prueba vigente, the SGCA shall permitir acceso completo a todas las funcionalidades de la plataforma
5. The SGCA shall permitir que el system admin acceda al panel de administración independientemente del estado del trial de cualquier tenant

---

### Requirement 6: Panel de Administración del Sistema
**Objective:** As system admin, I want un panel centralizado para gestionar todos los tenants, so that pueda supervisar el estado de la plataforma y aplicar cambios de plan y licencias sin intervención técnica manual en la base de datos

#### Acceptance Criteria
1. The SGCA shall proveer al system admin un panel que liste todos los tenants registrados mostrando: nombre de empresa, subdominio, plan actual, estado de acceso, fecha de vencimiento del trial (cuando aplique) y número de licencias asignadas
2. When el system admin selecciona un tenant desde el panel, the SGCA shall permitir realizar las operaciones: cambiar de Trial a Enterprise, asignar número de licencias, extender la fecha de vencimiento del trial
3. The SGCA shall restringir el acceso al panel de administración exclusivamente a usuarios con privilegios de superusuario del sistema
4. If un usuario sin privilegios de superusuario intenta acceder al panel de administración, the SGCA shall rechazar el acceso
5. The SGCA shall reflejar en el panel cualquier cambio aplicado a un tenant de forma inmediata, sin necesidad de recargar o sincronizar manualmente
