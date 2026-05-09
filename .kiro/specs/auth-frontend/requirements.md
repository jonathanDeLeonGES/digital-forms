# Requirements: auth-frontend

## Overview
Página de login React que consume el endpoint JWT ya existente (`POST /api/auth/login/`), guarda los tokens, protege las rutas de la app y provee un contexto de autenticación compartido.

---

## Requirements

### 1. Autenticación

#### 1.1 Formulario de login
- **Como** usuario del tenant, **quiero** ingresar mi email y contraseña en una página de login, **para** acceder al sistema.
- **Criterios**:
  - La página muestra campos `email` y `password`
  - El botón "Ingresar" está deshabilitado mientras se procesa la petición
  - El campo email valida formato básico antes de enviar
  - El campo password requiere al menos 1 carácter (validación server-side es suficiente)

#### 1.2 Llamada al API de login
- **Como** sistema, **quiero** enviar `POST /api/auth/login/` con `{email, password}`, **para** obtener los tokens JWT.
- **Criterios**:
  - Request con `Content-Type: application/json`
  - Respuesta 200: almacenar `access` y `refresh` en localStorage
  - Respuesta 401: mostrar mensaje genérico "Credenciales incorrectas." sin revelar si falla email o contraseña
  - Respuesta de red fallida: mostrar "No se pudo conectar con el servidor."

#### 1.3 Redirección post-login
- **Como** usuario, **quiero** ser redirigido automáticamente tras un login exitoso, **para** llegar directamente a mi destino.
- **Criterios**:
  - Login exitoso → redirige a `/issues` (o a la ruta que intentaba acceder antes del redirect)
  - Si ya está autenticado y visita `/login` → redirige a `/issues`

#### 1.4 Persistencia de sesión
- **Como** usuario, **quiero** que mi sesión persista al recargar la página, **para** no tener que hacer login en cada visita.
- **Criterios**:
  - Los tokens se guardan en `localStorage` (claves: `access_token`, `refresh_token`)
  - Al cargar la app, si existe `access_token` en localStorage, el usuario se considera autenticado
  - El token se decodifica (base64) para extraer `role` y leer el nombre del usuario

### 2. Rutas protegidas

#### 2.1 Guardia de rutas
- **Como** sistema, **quiero** redirigir al login cualquier ruta protegida que acceda un usuario no autenticado, **para** proteger los datos del tenant.
- **Criterios**:
  - Rutas protegidas: `/issues`, `/issues/*`
  - Usuario sin token → redirige a `/login`
  - La URL original se preserva en state para redirigir tras el login

#### 2.2 Manejo de token expirado
- **Como** sistema, **quiero** redirigir al login cuando la API retorna 401, **para** que el usuario renueve su sesión.
- **Criterios**:
  - Cualquier respuesta 401 desde el API de issues → limpiar tokens y redirigir a `/login`
  - Mostrar mensaje "Tu sesión expiró. Ingresa de nuevo." en la página de login

### 3. Contexto de autenticación

#### 3.1 Datos del usuario autenticado
- **Como** componente de la app, **quiero** acceder al usuario actual sin prop drilling, **para** mostrar nombre, rol y controlar permisos UI.
- **Criterios**:
  - `useAuth()` retorna `{ user, isAuthenticated, login, logout }`
  - `user` contiene: `{ id?, email?, role, nombre_completo? }`
  - `role` se lee del payload del JWT (claim `role`)
  - `nombre_completo` se lee del payload si está disponible, sino se muestra el email

#### 3.2 Logout
- **Como** usuario, **quiero** poder cerrar sesión, **para** proteger mi cuenta al compartir el equipo.
- **Criterios**:
  - Llamar `POST /api/auth/logout/` con `{refresh: <token>}`
  - Limpiar `access_token` y `refresh_token` de localStorage independientemente de la respuesta del servidor
  - Redirigir a `/login`
  - Un botón de logout visible en las páginas protegidas

### 4. UX

#### 4.1 Experiencia de login
- **Como** usuario, **quiero** feedback visual claro durante el proceso, **para** saber qué está pasando.
- **Criterios**:
  - Estado de carga: texto del botón cambia a "Ingresando..."
  - Error: banner rojo bajo el formulario con el mensaje de error
  - No se muestran mensajes de error de campos individuales para evitar enumerar usuarios válidos

#### 4.2 Accesibilidad básica
- **Criterios**:
  - Labels asociados a inputs (`htmlFor` + `id`)
  - Submit con Enter en cualquier campo del formulario
  - Focus en el campo email al cargar la página

#### 4.3 Enlace a registro de empresa
- **Como** visitante que llegó a la página de login pero cuya empresa aún no tiene cuenta en el SGCA, **quiero** un enlace que me lleve al formulario de registro de empresa, **para** poder crearla sin conocer la URL de antemano.
- **Criterios**:
  - La LoginPage muestra un enlace con el texto "¿Tu empresa aún no está en el SGCA? Regístrala aquí" que navega a `/register`
  - El texto deja claro que es para registrar una **empresa nueva**, no para crear un usuario dentro de una empresa existente (los usuarios los crea el admin del tenant)
  - El enlace es visible sin scroll en la mayoría de pantallas
