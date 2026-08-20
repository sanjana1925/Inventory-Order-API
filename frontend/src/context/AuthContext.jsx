import { createContext, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null)

// Keeping the whole session (role + profile + token) as one localStorage
// blob is simpler to reason about than three separate keys, and a page
// refresh just needs to parse it back once on load.
const STORAGE_KEY = 'ioma_auth'

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved) : null
  })

  useEffect(() => {
    if (auth) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [auth])

  // role is 'customer' (business client) or 'staff' (admin/staff) — decides
  // which pages/nav links a logged-in session sees.
  function login(role, profile, token) {
    setAuth({ role, profile, token })
  }

  function logout() {
    setAuth(null)
  }

  return (
    <AuthContext.Provider value={{ auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
