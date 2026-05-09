import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import RegisterPage from './pages/Register/RegisterPage'
import IssueListPage from './pages/issues/IssueListPage'
import IssueFormPage from './pages/issues/IssueFormPage'
import IssueDetailPage from './pages/issues/IssueDetailPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/issues" element={<IssueListPage />} />
        <Route path="/issues/new" element={<IssueFormPage />} />
        <Route path="/issues/:id/edit" element={<IssueFormPage />} />
        <Route path="/issues/:id" element={<IssueDetailPage />} />
        <Route path="*" element={<Navigate to="/register" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
