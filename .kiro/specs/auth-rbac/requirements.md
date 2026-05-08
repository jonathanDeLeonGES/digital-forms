# Requirements Document

## Project Description (Input)
Los usuarios de cada empresa en SGCA necesitan autenticarse de forma segura dentro de su tenant (subdominio) y el sistema debe controlar qué acciones puede realizar cada rol sin mezclar datos entre tenants. El tenant ya existe (creado por tenant-onboarding) pero no hay usuarios, autenticación ni permisos. Se necesita: custom user model con 4 roles (admin/responsable/supervisor/verificador), autenticación JWT con access/refresh tokens, CRUD de usuarios gestionado por el admin del tenant dentro del límite de licencias, y mixins de permiso por rol reutilizables en todos los specs de Wave 2+. Queda fuera: recuperación de contraseña por email (→ notificaciones), SSO/OAuth, 2FA.

## Introducción
SGCA Auth RBAC provee el sistema de autenticación JWT y control de acceso basado en roles (RBAC) para todos los tenants. Gestiona el ciclo de vida de usuarios dentro de cada tenant, la autenticación con tokens JWT firmados, la asignación de roles y la validación de límites de licencias. Los contratos de autenticación y permisos definidos en este spec son la base que todos los specs de Wave 2+ deben usar.

## Boundary Context
- **In scope**: Custom user model con rol, login/refresh/logout JWT, CRUD de usuarios por el admin del tenant, validación del límite de licencias al activar usuario, mixins/decoradores de permiso por rol, cambio de contraseña, endpoint de perfil propio
- **Out of scope**: Recuperación de contraseña por email (→ notificaciones), SSO/OAuth, 2FA, notificaciones de bienvenida por email, autenticación del system admin (usa Django superuser, no este spec)
- **Adjacent expectations**: Todos los specs de Wave 2+ usan los mixins de permiso de este spec. El middleware de tenant (→ tenant-onboarding) ya inyecta `request.tenant` antes de que este spec procese el request. El límite de licencias viene de `Subscription.num_licencias` del schema público (→ tenant-onboarding).

## Requirements

### Requirement 1: Autenticación JWT
**Objective:** As a usuario registrado, I want iniciar sesión con mis credenciales en el subdominio de mi empresa, so that obtenga tokens JWT válidos para operar en el sistema

#### Acceptance Criteria
1. When un usuario envía email y contraseña válidos al endpoint de login del tenant, the SGCA shall retornar un access token y un refresh token JWT firmados con expiración configurada
2. If el email o la contraseña son incorrectos, the SGCA shall rechazar el login con código 401 sin revelar cuál campo es incorrecto
3. If el usuario está desactivado, the SGCA shall rechazar el login con código 401 e informar que la cuenta está desactivada
4. When un usuario envía un refresh token válido al endpoint de refresh, the SGCA shall retornar un nuevo access token sin requerir credenciales
5. If el refresh token ha expirado o es inválido, the SGCA shall rechazar la renovación con código 401
6. When un usuario envía un refresh token válido al endpoint de logout, the SGCA shall invalidar ese refresh token, impidiendo renovaciones futuras con él
7. The SGCA shall garantizar que los tokens JWT de un tenant no sean aceptados como válidos en endpoints de otro tenant

---

### Requirement 2: Modelo de Usuario con Rol
**Objective:** As sistema SGCA, I want que cada usuario tenga exactamente un rol que determine sus permisos, so that el control de acceso sea predecible y consistente en todos los endpoints

#### Acceptance Criteria
1. The SGCA shall soportar exactamente cuatro roles de usuario: admin, responsable, supervisor, verificador
2. The SGCA shall requerir que cada usuario tenga exactamente un rol asignado; un usuario no puede tener múltiples roles simultáneamente
3. The SGCA shall garantizar que cada usuario pertenezca a exactamente un tenant y no pueda acceder a datos de otro tenant
4. When un admin del tenant crea un usuario, the SGCA shall requerir nombre completo, email, contraseña y rol como campos obligatorios
5. The SGCA shall asegurar que el email de un usuario sea único dentro de su tenant

---

### Requirement 3: Gestión de Usuarios por el Admin del Tenant
**Objective:** As admin del tenant, I want crear, editar y desactivar usuarios de mi empresa, so that pueda gestionar el equipo que opera el sistema

#### Acceptance Criteria
1. When el admin del tenant solicita listar usuarios, the SGCA shall retornar todos los usuarios del tenant con nombre, email, rol y estado (activo/inactivo)
2. When el admin del tenant crea un nuevo usuario con datos válidos, the SGCA shall crear el usuario en el schema del tenant activo y retornar los datos del usuario creado
3. When el admin del tenant edita un usuario existente, the SGCA shall permitir actualizar nombre, email o rol, y retornar los datos actualizados
4. When el admin del tenant desactiva un usuario, the SGCA shall marcar al usuario como inactivo impidiendo que inicie sesión, sin eliminar sus datos ni historial
5. If el usuario solicitado no pertenece al tenant activo, the SGCA shall rechazar la operación con código 404
6. The SGCA shall restringir el listado, creación, edición y desactivación de usuarios exclusivamente al rol admin del tenant

---

### Requirement 4: Validación del Límite de Licencias
**Objective:** As sistema SGCA, I want que el número de usuarios activos no exceda el límite de licencias del plan Enterprise, so that se respeten los términos del plan contratado

#### Acceptance Criteria
1. If el tenant tiene plan Enterprise y el número de usuarios activos ya alcanzó el límite de licencias, the SGCA shall rechazar la creación o reactivación de usuarios adicionales con código 400 e informar que se alcanzó el límite de licencias
2. While el tenant tiene plan Trial, the SGCA shall permitir la creación de usuarios sin restricción por número de licencias
3. When un usuario es desactivado, the SGCA shall contabilizar ese usuario como inactivo, liberando una licencia disponible para el tenant

---

### Requirement 5: Control de Acceso por Rol
**Objective:** As sistema SGCA, I want que cada endpoint verifique automáticamente el rol del usuario autenticado, so that ningún usuario pueda ejecutar operaciones fuera de su rol asignado

#### Acceptance Criteria
1. While procesando cualquier request a un endpoint protegido, the SGCA shall verificar que el request incluya un JWT válido y no expirado antes de procesar la solicitud
2. If el usuario autenticado no tiene el rol requerido por el endpoint, the SGCA shall rechazar el request con código 403
3. The SGCA shall proveer clases de permiso reutilizables que los specs de Wave 2+ puedan usar para declarar el rol requerido por endpoint sin duplicar lógica
4. If el access token JWT del request ha expirado, the SGCA shall rechazar el request con código 401

---

### Requirement 6: Gestión de Perfil Propio
**Objective:** As usuario autenticado, I want ver y actualizar mi información y cambiar mi contraseña, so that pueda mantener mis datos de acceso actualizados

#### Acceptance Criteria
1. When un usuario autenticado solicita su perfil, the SGCA shall retornar su nombre, email, rol y estado
2. When un usuario autenticado actualiza su nombre o email en su perfil, the SGCA shall validar y guardar los cambios
3. When un usuario autenticado envía contraseña actual y nueva contraseña, the SGCA shall validar la contraseña actual y actualizar la contraseña si es correcta
4. If la contraseña actual proporcionada es incorrecta, the SGCA shall rechazar el cambio con código 400
5. If el nuevo email ya está en uso por otro usuario del mismo tenant, the SGCA shall rechazar el cambio con código 400
