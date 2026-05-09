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

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Rutas públicas */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Rutas protegidas con NavBar */}
          <Route element={<PrivateRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/issues" element={<IssueListPage />} />
              <Route path="/issues/new" element={<IssueFormPage />} />
              <Route path="/issues/:id/edit" element={<IssueFormPage />} />
              <Route path="/issues/:id" element={<IssueDetailPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
