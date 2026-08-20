import { useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import Card from '../components/Card'

export default function ProfilePage() {
  const { auth, login } = useAuth()
  const [form, setForm] = useState({
    name: auth.profile.name || '',
    phone: auth.profile.phone || '',
    address: auth.profile.address || '',
  })
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setSaved(false)
  }

  async function saveProfile(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const updated = await api.put(`/customers/${auth.profile.id}`, form)
      login('customer', updated, auth.token)
      setSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const initials = (form.name || auth.profile.email || '??').slice(0, 2).toUpperCase()

  return (
    <div className="max-w-md">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-yellow-400 text-base font-semibold text-slate-900">
          {initials}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Company Profile</h1>
          <p className="text-sm text-slate-500">{auth.profile.email}</p>
        </div>
      </div>
      <Card>
        <form onSubmit={saveProfile} className="flex flex-col gap-3">
          <label className="text-sm text-gray-500">Email</label>
          <input className="border border-slate-300 rounded-lg px-3 py-2 bg-slate-100 text-slate-500" value={auth.profile.email} disabled />

          <label className="text-sm text-gray-500">Company / contact name</label>
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
            value={form.name}
            onChange={(e) => updateField('name', e.target.value)}
          />

          <label className="text-sm text-gray-500">Phone</label>
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
            value={form.phone}
            onChange={(e) => updateField('phone', e.target.value)}
          />

          <label className="text-sm text-gray-500">Address</label>
          <textarea
            className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
            rows={2}
            value={form.address}
            onChange={(e) => updateField('address', e.target.value)}
          />

          {error && <p className="text-red-600 text-sm">{error}</p>}
          {saved && <p className="text-green-700 text-sm">Saved.</p>}
          <button disabled={busy} className="bg-yellow-400 hover:bg-yellow-500 disabled:opacity-50 text-slate-900 font-medium rounded-lg px-3 py-2 self-start">
            Save
          </button>
        </form>
      </Card>
    </div>
  )
}
