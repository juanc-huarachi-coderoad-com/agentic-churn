import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { LoginPage } from './auth/login-page'
import { ProtectedRoute } from './auth/protected-route'
import { CoveragePage } from './coverage/coverage-page'
import { DashboardPage } from './dashboard/dashboard-page'
import { ProfileEditorForm } from './profile-editor/profile-editor-form'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/coverage"
          element={
            <ProtectedRoute>
              <CoveragePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <ProfileEditorForm />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
