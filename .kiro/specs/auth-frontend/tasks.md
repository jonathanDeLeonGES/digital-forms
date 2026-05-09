# Implementation Plan — auth-frontend

- [x] 1. Servicio de autenticación
- [x] 1.1 Implementar `auth.ts` con helpers de token y llamadas API
  - Implementar `saveTokens(access, refresh)`, `clearTokens()`, `getAccessToken()`, `getRefreshToken()`
  - Implementar `decodeToken(token)` — base64 decode del payload sin librería externa
  - Implementar `isTokenValid()` — compara `exp` claim con `Date.now() / 1000`
  - Implementar `getUserFromToken()` — retorna `AuthUser | null` desde el token en localStorage
  - Implementar `loginApi(email, password)` — POST `/api/auth/login/` → retorna `{access, refresh}`, lanza error en 401/red
  - Implementar `logoutApi(refresh)` — POST `/api/auth/logout/` con `{refresh}`
  - Observable: `decodeToken` extrae `role` y `user_id` correctamente; `isTokenValid` retorna false para token con `exp` en el pasado
  - _Requirements: 1.2, 1.4, 3.1_

- [x] 2. Contexto de autenticación
- [x] 2.1 Implementar `AuthContext.tsx` y `useAuth()`
  - `AuthProvider` inicializa estado desde `getUserFromToken()` al montar (persistencia de sesión)
  - `login(email, password)` llama `loginApi`, guarda tokens, actualiza `user` en estado
  - `logout()` llama `logoutApi`, limpia tokens, resetea `user` a null
  - `useAuth()` hook que consume el contexto y lanza error si se usa fuera del provider
  - Observable: tras `login()` exitoso, `isAuthenticated` es `true` y `user.role` refleja el claim del JWT
  - _Requirements: 1.2, 1.3, 1.4, 3.1, 3.2_

- [x] 3. Página de login
- [x] 3.1 (P) Implementar `LoginPage.tsx` y sus tests
  - Formulario con campos `email` (type=email, autoFocus) y `password` (type=password)
  - Submit llama `authContext.login(email, password)` → en éxito navega a `state.from ?? '/issues'`
  - Error 401 → muestra banner "Credenciales incorrectas."
  - Error de red → muestra banner "No se pudo conectar con el servidor."
  - Botón deshabilitado y texto "Ingresando..." durante la llamada
  - Si `isAuthenticated` al montar → redirect a `/issues`
  - Incluir enlace "¿Tu empresa aún no está en el SGCA? Regístrala aquí" que navega a `/register`
  - Tests (TDD): campos presentes, submit sin email no llama API, login exitoso redirige, 401 muestra error, red error muestra error, botón deshabilitado mientras carga, enlace a registro visible
  - Observable: `npm test` pasa; `LoginPage` muestra errores correctos para 401 y error de red
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3_

- [x] 4. Protección de rutas
- [x] 4.1 (P) Implementar `PrivateRoute.tsx` y actualizar `App.tsx`
  - `PrivateRoute` verifica `isAuthenticated`; si false → `<Navigate to="/login" state={{ from: location }} />`; si true → `<Outlet />`
  - Actualizar `App.tsx`: envolver rutas `/issues/*` con `<PrivateRoute />`; añadir ruta `/login`; cambiar redirect `*` de `/register` a `/login`
  - Envolver la app con `<AuthProvider>` en `main.tsx` o `App.tsx`
  - Observable: sin token en localStorage, navegar a `/issues` redirige a `/login`; tras login exitoso, `/issues` carga normalmente
  - _Requirements: 2.1, 2.2, 1.3_

- [x] 5. Botón de logout en la app
- [x] 5.1 Implementar botón de logout visible en páginas protegidas
  - Añadir barra de navegación mínima (`NavBar.tsx`) con nombre/rol del usuario y botón "Cerrar sesión"
  - Cerrar sesión llama `authContext.logout()` → redirige a `/login`
  - La barra solo aparece en rutas dentro de `<PrivateRoute />`
  - Observable: clic en "Cerrar sesión" limpia localStorage y muestra la página de login
  - _Requirements: 3.2_
