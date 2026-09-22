import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/layout/ProtectedRoute'

import Dashboard from './pages/Dashboard'
import Contacts from './pages/Contacts'
import Threats from './pages/Threats'
import Call from './pages/Call'
import Login from './pages/Login'
import Signup from './pages/Signup'
import CallSecurityReport from './pages/CallSecurityReport'
import Landing from './pages/Landing'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/landing" element={<Landing />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route
              path="/dashboard"
              element={<Dashboard />}
            />

            <Route
              path="/contacts"
              element={<Contacts />}
            />

            <Route
              path="/threats"
              element={<Threats />}
            />

            <Route
              path="/call/:callId"
              element={<Call />}
            />
            <Route
              path="/call/:callId/report"
              element={<CallSecurityReport />}
            />
          </Route>
        </Route>

        {/* Default route */}
        <Route path="/" element={<Landing />} />

        {/* Unknown route */}
        <Route
          path="*"
          element={<Navigate to="/dashboard" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App