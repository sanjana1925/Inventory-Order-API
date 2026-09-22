import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import Card from '../components/Card'

const STATUS_BADGE = {
  open: 'bg-yellow-50 text-yellow-700',
  closed: 'bg-slate-100 text-slate-600',
}

// One page covers both /support (customer) and /admin/support (staff), same
// reasoning as QuotesPage — branch on auth.role instead of two thin files.
export default function SupportPage() {
  const { auth } = useAuth()
  const isStaff = auth.role === 'staff'
  const [tickets, setTickets] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const [form, setForm] = useState({ subject: '', message: '', email: auth.profile.email || '' })

  function loadTickets() {
    const path = isStaff ? '/support?status=open' : `/support?customer_id=${auth.profile.id}`
    api.get(path).then(setTickets).catch((err) => setError(err.message))
  }

  useEffect(loadTickets, [isStaff, auth.profile.id])

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function createTicket(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/support', {
        customer_name: auth.profile.name,
        customer_id: auth.profile.id,
        email: form.email,
        subject: form.subject,
        message: form.message,
      })
      setForm({ subject: '', message: '', email: form.email })
      loadTickets()
    } catch (err) {
      setError(err.message)
    }
  }

  async function closeTicket(id) {
    setBusyId(id)
    setError('')
    try {
      await api.post(`/support/${id}/close`)
      loadTickets()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-4">Support</h1>
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      {!isStaff && (
        <Card title="Need help?" className="mb-4">
          <form onSubmit={createTicket} className="flex flex-col gap-3">
            <input
              className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
              type="email"
              placeholder="Your email"
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              required
            />
            <input
              className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
              placeholder="Subject"
              value={form.subject}
              onChange={(e) => updateField('subject', e.target.value)}
              required
            />
            <textarea
              className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
              placeholder="Message"
              rows={3}
              value={form.message}
              onChange={(e) => updateField('message', e.target.value)}
              required
            />
            <button className="bg-yellow-400 hover:bg-yellow-500 text-slate-900 font-medium rounded-lg px-3 py-2 self-start">
              Submit ticket
            </button>
          </form>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {tickets.map((t) => (
          <Card key={t.id}>
            <div className="flex justify-between items-start">
              <div>
                <p className="font-medium text-slate-900">
                  {t.subject}{isStaff ? ` · ${t.customer_name}` : ''}
                </p>
                <p className="text-sm text-gray-500">{new Date(t.created_at).toLocaleString()} &middot; {t.email}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_BADGE[t.status] || 'bg-slate-100 text-slate-600'}`}>
                {t.status}
              </span>
            </div>
            <p className="text-sm text-gray-700 mt-2">{t.message}</p>
            {isStaff && t.status === 'open' && (
              <button
                disabled={busyId === t.id}
                onClick={() => closeTicket(t.id)}
                className="mt-3 bg-slate-700 hover:bg-slate-800 disabled:opacity-50 text-white rounded-lg px-3.5 py-1.5 text-sm font-medium"
              >
                Close
              </button>
            )}
          </Card>
        ))}
        {tickets.length === 0 && <p className="text-gray-500">No tickets.</p>}
      </div>
    </div>
  )
}
