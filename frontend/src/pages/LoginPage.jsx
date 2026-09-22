import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'

// Design system for this page: Background (yellow-50, calm) / Text (slate-900,
// high contrast) / Primary (slate-800, the brand panel) / Secondary
// (slate-100, the tab switcher) / Accent-CTA (yellow-400, every button/link).
const INPUT =
  'rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400'
const CTA =
  'mt-1 rounded-xl bg-yellow-400 px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-yellow-500 disabled:opacity-50'

export default function LoginPage() {
  const [tab, setTab] = useState('customer') // 'customer' | 'staff'
  const [customerAction, setCustomerAction] = useState('login') // 'login' | 'signup'
  const [form, setForm] = useState({ name: '', email: '', password: '', phone: '', address: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleCustomerSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const path = customerAction === 'signup' ? '/customers/signup' : '/customers/login'
      const body =
        customerAction === 'signup'
          ? { name: form.name, email: form.email, password: form.password, phone: form.phone || undefined, address: form.address || undefined }
          : { email: form.email, password: form.password }
      const data = await api.post(path, body)
      const { access_token, token_type, ...profile } = data
      login('customer', profile, access_token)
      navigate('/catalog')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleStaffSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const data = await api.post('/auth/login', { email: form.email, password: form.password })
      const { access_token, token_type, ...profile } = data
      login('staff', profile, access_token)
      navigate('/admin')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const heading = tab === 'staff' ? 'Admin / staff login' : customerAction === 'signup' ? 'Create your account' : 'Welcome back'

  return (
    <div className="flex min-h-screen items-center justify-center bg-yellow-50 p-4">
      <div className="flex w-full max-w-4xl overflow-hidden rounded-3xl bg-white shadow-xl">
        {/* Brand panel — Primary color, hidden on small screens */}
        <div className="hidden w-5/12 flex-col justify-between bg-slate-800 p-10 text-white md:flex">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-yellow-400 text-sm font-bold text-slate-900">
              IO
            </span>
            <span className="text-lg font-bold">Inventory & Orders</span>
          </div>

          <div>
            <h2 className="text-3xl font-bold leading-tight">Run your inventory with confidence</h2>
            <p className="mt-3 text-sm text-slate-300">
              Track stock, manage orders, and keep your business and clients in sync — all from one place.
            </p>
          </div>

          <p className="text-xs text-slate-400">A local demo B2B portal — not for production use.</p>
        </div>

        {/* Form panel — Background color */}
        <div className="w-full p-8 sm:p-10 md:w-7/12">
          <h1 className="text-2xl font-bold text-slate-900">{heading}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {tab === 'staff' ? 'Sign in with your admin or staff account.' : 'Access the business client portal.'}
          </p>

          {/* Role switcher — Secondary color */}
          <div className="my-6 inline-flex rounded-lg bg-slate-100 p-1 text-sm">
            <button
              type="button"
              className={`rounded-md px-4 py-1.5 font-medium transition-colors ${
                tab === 'customer' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
              onClick={() => { setTab('customer'); setError('') }}
            >
              Business client
            </button>
            <button
              type="button"
              className={`rounded-md px-4 py-1.5 font-medium transition-colors ${
                tab === 'staff' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
              onClick={() => { setTab('staff'); setError('') }}
            >
              Admin / staff
            </button>
          </div>

          {tab === 'customer' && (
            <>
              <div className="mb-4 flex gap-4 text-sm text-slate-600">
                <label className="flex items-center gap-1.5">
                  <input
                    type="radio"
                    className="accent-yellow-500"
                    checked={customerAction === 'login'}
                    onChange={() => setCustomerAction('login')}
                  />
                  Log in
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="radio"
                    className="accent-yellow-500"
                    checked={customerAction === 'signup'}
                    onChange={() => setCustomerAction('signup')}
                  />
                  Sign up
                </label>
              </div>

              <form onSubmit={handleCustomerSubmit} className="flex flex-col gap-3">
                {customerAction === 'signup' && (
                  <input
                    className={INPUT}
                    placeholder="Company / contact name"
                    value={form.name}
                    onChange={(e) => updateField('name', e.target.value)}
                    required
                  />
                )}
                <input
                  className={INPUT}
                  type="email"
                  placeholder="Email"
                  value={form.email}
                  onChange={(e) => updateField('email', e.target.value)}
                  required
                />
                <input
                  className={INPUT}
                  type="password"
                  placeholder="Password"
                  value={form.password}
                  onChange={(e) => updateField('password', e.target.value)}
                  required
                  minLength={customerAction === 'signup' ? 6 : undefined}
                />
                {customerAction === 'signup' && (
                  <>
                    <input
                      className={INPUT}
                      placeholder="Phone (optional)"
                      value={form.phone}
                      onChange={(e) => updateField('phone', e.target.value)}
                    />
                    <input
                      className={INPUT}
                      placeholder="Address (optional)"
                      value={form.address}
                      onChange={(e) => updateField('address', e.target.value)}
                    />
                  </>
                )}
                {error && <p className="text-sm text-red-600">{error}</p>}
                <button disabled={busy} className={CTA}>
                  {customerAction === 'signup' ? 'Sign up' : 'Log in'}
                </button>
              </form>
            </>
          )}

          {tab === 'staff' && (
            <form onSubmit={handleStaffSubmit} className="flex flex-col gap-3">
              <input
                className={INPUT}
                type="email"
                placeholder="Email"
                value={form.email}
                onChange={(e) => updateField('email', e.target.value)}
                required
              />
              <input
                className={INPUT}
                type="password"
                placeholder="Password"
                value={form.password}
                onChange={(e) => updateField('password', e.target.value)}
                required
              />
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button disabled={busy} className={CTA}>Log in</button>
              <p className="text-xs text-slate-400">
                Admin/staff accounts are created via the API's bootstrap route (POST /users), not from this UI.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
