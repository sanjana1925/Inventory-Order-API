import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import Card from '../components/Card'

// Covers both /notifications (customer, audience=client) and
// /admin/notifications (staff, audience=admin) — same list rendering either way.
const LEVEL_STYLES = {
  critical: 'border-l-4 border-red-500',
  warning: 'border-l-4 border-amber-400',
  info: 'border-l-4 border-gray-300',
}
const LEVEL_DOT = {
  critical: 'bg-red-500',
  warning: 'bg-amber-500',
  info: 'bg-indigo-500',
}

export default function NotificationsPage() {
  const { auth } = useAuth()
  const isStaff = auth.role === 'staff'
  const audience = isStaff ? 'admin' : 'client'
  const [notifications, setNotifications] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get(`/notifications?audience=${audience}&limit=50`)
      .then(setNotifications)
      .catch((err) => setError(err.message))
  }, [audience])

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-4">Notifications</h1>
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      <div className="flex flex-col gap-2">
        {notifications.map((n) => (
          <Card key={n.id} className={LEVEL_STYLES[n.level] || ''}>
            <div className="flex justify-between items-start gap-3">
              <div className="flex items-start gap-2.5">
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${LEVEL_DOT[n.level] || 'bg-slate-400'}`} />
                <p className="text-sm text-slate-900">{n.message}</p>
              </div>
              <p className="text-xs text-gray-500 whitespace-nowrap">{new Date(n.created_at).toLocaleString()}</p>
            </div>
            {n.order_id && <p className="text-xs text-gray-500 mt-1 ml-4.5">Order #{n.order_id}</p>}
          </Card>
        ))}
        {notifications.length === 0 && <p className="text-gray-500">No notifications.</p>}
      </div>
    </div>
  )
}
