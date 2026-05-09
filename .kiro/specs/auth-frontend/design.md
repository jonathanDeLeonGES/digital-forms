# Design: auth-frontend

## Overview

auth-frontend añade la capa de identidad al frontend React del SGCA. Consume el endpoint `POST /api/auth/login/` ya implementado en `auth-rbac`, almacena los tokens JWT en localStorage, decodifica el payload para extraer `role` y expone un `AuthContext` que todos los módulos de Wave 2+ pueden consumir.

**Purpose**: Dar a los usuarios una forma de autenticarse en el frontend y proteger las rutas de la app.
**Users**: Todos los usuarios del tenant (admin, responsable, supervisor, verificador).
**Impact**: Habilita el E2E en navegador para todos los specs de Wave 2+. Sin esta pieza, los tests de browser no pueden autenticarse.

### Goals
- LoginPage con validación client-side mínima y manejo de errores del API
- AuthContext con `useAuth()` hook compartido
- PrivateRoute que redirige a `/login` si no hay token
- Logout con blacklist del refresh token

### Non-Goals
- Recuperación de contraseña (→ notificaciones, Wave 4)
- Página de perfil/cambio de contraseña (→ futura iteración de auth-frontend)
- User management UI / panel de admin de usuarios (→ futura spec)
- Token refresh automático con interceptor (primera iteración: 401 → redirect a login)
- SSO/OAuth, 2FA

---

## Boundary Commitments

### This Spec Owns
- `frontend/src/services/auth.ts` — login(), logout() API calls + token storage helpers
- `frontend/src/context/AuthContext.tsx` — React context + useAuth() hook
- `frontend/src/pages/Login/LoginPage.tsx` + test
- `frontend/src/components/PrivateRoute.tsx` — route guard
- Actualización de `frontend/src/App.tsx` — rutas protegidas con PrivateRoute

### Out of Boundary
- Backend JWT endpoints (`POST /api/auth/login/` etc.) — ya implementados en `auth-rbac`
- Gestión de usuarios UI (CRUD de usuarios del tenant) — futura spec
- Página de perfil — futura spec
- Refresh automático de access token — futura iteración

### Allowed Dependencies
- `auth-rbac`: endpoint `POST /api/auth/login/` (responde `{access, refresh}`)
- `auth-rbac`: endpoint `POST /api/auth/logout/` (recibe `{refresh}`)
- JWT payload claims: `role`, `tenant`, `user_id` (según `CustomTokenObtainPairSerializer`)
- `react-router-dom` v6: `Navigate`, `useNavigate`, `useLocation`, `Outlet`

### Revalidation Triggers
- Si `auth-rbac` cambia los claims del JWT (`role`, `tenant`), actualizar `decodeToken()` en `auth.ts`
- Si se agrega `nombre_completo` como claim del JWT, actualizar `AuthContext` para leerlo del token
- Si se implementa refresh automático, reemplazar el redirect-on-401 por interceptor en `issuesService`

---

## Architecture

### File Structure

```
frontend/src/
├── services/
│   └── auth.ts                    # login(), logout(), getTokens(), clearTokens(), decodeToken()
├── context/
│   └── AuthContext.tsx            # AuthProvider, useAuth()
├── components/
│   └── PrivateRoute.tsx           # Wrapper que verifica isAuthenticated
├── pages/
│   └── Login/
│       ├── LoginPage.tsx
│       └── LoginPage.test.tsx
└── App.tsx                        # Actualizado con rutas protegidas
```

### Flow

```
Usuario visita /issues
    → PrivateRoute verifica localStorage['access_token']
    → Si no hay token → Navigate to /login (state: { from: /issues })
    → LoginPage muestra formulario
    → Submit → authService.login(email, password)
        → POST /api/auth/login/
        → 200: guardar tokens → navigate(state.from ?? '/issues')
        → 401: mostrar "Credenciales incorrectas."
    → /issues carga normalmente con token en headers
```

---

## Components and Interfaces

### `frontend/src/services/auth.ts`

```typescript
interface TokenPayload {
  user_id: number
  email?: string
  role: string      // 'admin' | 'responsable' | 'supervisor' | 'verificador'
  tenant: string    // schema_name del tenant
  exp: number
}

interface AuthUser {
  id: number
  email: string
  role: string
  tenant: string
  nombre_completo?: string
}

// Storage helpers
export function saveTokens(access: string, refresh: string): void
export function clearTokens(): void
export function getAccessToken(): string | null
export function getRefreshToken(): string | null
export function decodeToken(token: string): TokenPayload | null

// API calls
export async function loginApi(email: string, password: string): Promise<{ access: string; refresh: string }>
export async function logoutApi(refresh: string): Promise<void>

// Derived state
export function getUserFromToken(): AuthUser | null
export function isTokenValid(): boolean   // checks exp claim against Date.now()
```

### `frontend/src/context/AuthContext.tsx`

```typescript
interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>   // throws on error
  logout: () => Promise<void>
}

export function AuthProvider({ children }: { children: ReactNode }): JSX.Element
export function useAuth(): AuthContextValue
```

### `frontend/src/components/PrivateRoute.tsx`

```typescript
// Renders <Outlet /> if authenticated, else <Navigate to="/login" state={{ from: location }} />
export default function PrivateRoute(): JSX.Element
```

### `frontend/src/pages/Login/LoginPage.tsx`

```typescript
// Form: email + password → authContext.login() → navigate(from ?? '/issues')
// Error states: 'Credenciales incorrectas.' | 'No se pudo conectar con el servidor.'
```

### `frontend/src/App.tsx` (actualizado)

```tsx
<Routes>
  <Route path="/register" element={<RegisterPage />} />
  <Route path="/login" element={<LoginPage />} />
  <Route element={<PrivateRoute />}>
    <Route path="/issues" element={<IssueListPage />} />
    <Route path="/issues/new" element={<IssueFormPage />} />
    <Route path="/issues/:id/edit" element={<IssueFormPage />} />
    <Route path="/issues/:id" element={<IssueDetailPage />} />
  </Route>
  <Route path="*" element={<Navigate to="/login" replace />} />
</Routes>
```

---

## Data Models

### localStorage keys

| Key | Valor | Descripción |
|-----|-------|-------------|
| `access_token` | JWT string | Access token (15 min TTL) |
| `refresh_token` | JWT string | Refresh token (7 días TTL) |

### JWT Payload (decodificado)

```json
{
  "user_id": 1,
  "email": "admin@empresa.com",
  "role": "admin",
  "tenant": "empresa",
  "exp": 1234567890,
  "iat": 1234567000
}
```

*Nota: `email` y `nombre_completo` pueden no estar en el payload actual de `auth-rbac`. Si solo está `user_id` y `role`, mostrar el email del formulario de login como fallback.*

---

## Error Handling

| Escenario | Respuesta API | Mensaje en UI |
|-----------|--------------|---------------|
| Credenciales incorrectas | 401 | "Credenciales incorrectas." |
| Usuario inactivo | 401 | "Credenciales incorrectas." (mismo mensaje, no revelar motivo) |
| Sin conexión | network error | "No se pudo conectar con el servidor." |
| Token expirado (uso de app) | 401 desde issues API | Limpiar tokens + redirect `/login` con mensaje "Tu sesión expiró." |

---

## Testing Strategy

### Unit/Integration (Vitest + Testing Library)

1. `LoginPage.test.tsx`:
   - Muestra campos email y password
   - Submit sin email → no llama API (validación básica)
   - Submit con credenciales → llama `authService.login()`
   - Login exitoso → redirige a `/issues`
   - Login 401 → muestra "Credenciales incorrectas."
   - Error de red → muestra mensaje de conexión
   - Botón deshabilitado mientras carga

2. `PrivateRoute` (probado implícitamente en IssueListPage tests con mock de AuthContext)

3. `auth.ts`:
   - `decodeToken()` extrae payload correctamente
   - `isTokenValid()` retorna false para token expirado
   - `saveTokens()` / `clearTokens()` operan sobre localStorage
