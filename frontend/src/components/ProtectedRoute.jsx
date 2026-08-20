import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Client-side gating only, same as the Streamlit app — good enough for a
// demo UI, not a security boundary (the API itself is what enforces access
// on staff-only endpoints via the bearer token).
export default function ProtectedRoute({ role, children }) {
  const { auth } = useAuth()
  if (!auth || auth.role !== role) {
    return <Navigate to="/login" replace />
  }
  return children
}
