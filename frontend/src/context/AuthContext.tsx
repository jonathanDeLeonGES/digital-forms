import { createContext, useContext, useState, type ReactNode } from 'react'
import {
  loginApi,
  logoutApi,
  saveTokens,
  clearTokens,
  getRefreshToken,
  getUserFromToken,
  isTokenValid,
  type AuthUser,
} from '../services/auth'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() =>
    isTokenValid() ? getUserFromToken() : null,
  )

  async function login(email: string, password: string): Promise<void> {
    const { access, refresh } = await loginApi(email, password)
    saveTokens(access, refresh)
    setUser(getUserFromToken())
  }

  async function logout(): Promise<void> {
    const refresh = getRefreshToken()
    if (refresh) await logoutApi(refresh)
    clearTokens()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: user !== null, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
