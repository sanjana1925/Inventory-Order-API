import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/products', label: 'Products' },
  { to: '/admin/orders', label: 'Orders' },
  { to: '/admin/customers', label: 'Customers' },
  { to: '/admin/categories', label: 'Categories' },
  { to: '/admin/suppliers', label: 'Suppliers' },
  { to: '/admin/purchase-orders', label: 'Purchase Orders' },
  { to: '/admin/quotes', label: 'Quotes' },
  { to: '/admin/support', label: 'Support' },
  { to: '/admin/notifications', label: 'Notifications' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/reports', label: 'Reports' },
]

export default function AdminSidebar() {
  const { auth, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside className="flex w-60 shrink-0 flex-col bg-slate-800 px-5 pt-7 pb-6 text-white">
      <span className="text-base font-bold">Inventory & Orders</span>

      <nav className="mt-5 flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] ${
                isActive
                  ? 'bg-yellow-400 font-semibold text-slate-900'
                  : 'font-medium text-slate-400 hover:text-slate-200'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-slate-900' : 'bg-slate-400'}`} />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t border-slate-700 pt-4">
        <p className="truncate text-sm font-semibold">{auth?.profile?.email}</p>
        <p className="text-xs capitalize text-slate-400">{auth?.profile?.role || 'staff'}</p>
        <button
          onClick={handleLogout}
          className="mt-3 rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 hover:text-white"
        >
          Log out
        </button>
      </div>
    </aside>
  )
}
