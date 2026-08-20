import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const CUSTOMER_LINKS = [
  { to: '/catalog', label: 'Catalog' },
  { to: '/quick-order', label: 'Quick Order' },
  { to: '/favorites', label: 'Favorites' },
  { to: '/my-orders', label: 'My Orders' },
  { to: '/quotes', label: 'Quotes' },
  { to: '/addresses', label: 'Addresses' },
  { to: '/support', label: 'Support' },
  { to: '/notifications', label: 'Notifications' },
  { to: '/profile', label: 'Profile' },
]

export default function Navbar() {
  const { auth, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const initials = (auth?.profile?.name || auth?.profile?.email || '??').slice(0, 2).toUpperCase()

  return (
    <nav className="bg-slate-800 text-white px-4 py-2.5 flex items-center gap-1 flex-wrap">
      <div className="flex items-center gap-2 pr-4 mr-1">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-yellow-400 text-xs font-bold text-slate-900">
          IO
        </span>
        <span className="font-semibold">Inventory & Orders</span>
      </div>

      {auth?.role === 'customer' &&
        CUSTOMER_LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `rounded-lg px-3 py-1.5 text-sm transition-colors ${
                isActive ? 'bg-yellow-400 font-semibold text-slate-900' : 'text-slate-300 hover:bg-slate-700 hover:text-white'
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}

      <div className="ml-auto flex items-center gap-3">
        {auth && (
          <>
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-600 text-xs font-semibold text-white">
              {initials}
            </div>
            <span className="text-sm text-slate-300">{auth.role === 'customer' ? auth.profile.name : auth.profile.email}</span>
            <button onClick={handleLogout} className="text-sm bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg">
              Log out
            </button>
          </>
        )}
        {!auth && <NavLink to="/login" className="hover:text-slate-300">Login</NavLink>}
      </div>
    </nav>
  )
}
