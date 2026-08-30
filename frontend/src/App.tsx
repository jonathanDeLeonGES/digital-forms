import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import AppLayout from './components/AppLayout'
import LandingPage from './pages/Landing/LandingPage'
import RegisterPage from './pages/Register/RegisterPage'
import LoginPage from './pages/Login/LoginPage'
import IssueListPage from './pages/issues/IssueListPage'
import IssueFormPage from './pages/issues/IssueFormPage'
import IssueDetailPage from './pages/issues/IssueDetailPage'
import AccionListPage from './pages/acciones/AccionListPage'
import AccionDetailPage from './pages/acciones/AccionDetailPage'
import AccionFormPage from './pages/acciones/AccionFormPage'
import UserListPage from './pages/admin/UserListPage'
import UserFormPage from './pages/admin/UserFormPage'
import PlanTrabajoPage from './pages/planes/PlanTrabajoPage'
import { getSubdomain, getRootUrl } from './utils/subdomain'

function TenantApp() {
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // Validate tenant exists by probing the login endpoint.
    // Valid tenant → 401 or 405. Invalid tenant (no schema) → 404.
    fetch('/api/auth/login/', { method: 'GET' }).then((r) => {
      if (r.status === 404) window.location.replace(getRootUrl())
      else setChecking(false)
    }).catch(() => setChecking(false))
  }, [])

  if (checking) return null

  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<PrivateRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/issues" element={<IssueListPage />} />
              <Route path="/issues/new" element={<IssueFormPage />} />
              <Route path="/issues/:id/edit" element={<IssueFormPage />} />
              <Route path="/issues/:id" element={<IssueDetailPage />} />
              <Route path="/acciones" element={<AccionListPage />} />
              <Route path="/acciones/new" element={<AccionFormPage />} />
              <Route path="/acciones/:id/edit" element={<AccionFormPage />} />
              <Route path="/acciones/:id" element={<AccionDetailPage />} />
              <Route path="/acciones/:accionId/plan" element={<PlanTrabajoPage />} />
              <Route path="/admin/usuarios" element={<UserListPage />} />
              <Route path="/admin/usuarios/new" element={<UserFormPage />} />
              <Route path="/admin/usuarios/:id/edit" element={<UserFormPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

function PublicApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default function App() {
  const subdomain = getSubdomain()
  return subdomain ? <TenantApp /> : <PublicApp />
}
