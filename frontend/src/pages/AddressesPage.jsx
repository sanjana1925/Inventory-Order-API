import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import Card from '../components/Card'

export default function AddressesPage() {
  const { auth } = useAuth()
  const customerId = auth.profile.id
  const [addresses, setAddresses] = useState([])
  const [error, setError] = useState('')
  const [form, setForm] = useState({ label: '', address: '', is_default: false })

  function loadAddresses() {
    api.get(`/customers/${customerId}/addresses`).then(setAddresses).catch((err) => setError(err.message))
  }

  useEffect(loadAddresses, [customerId])

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function addAddress(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post(`/customers/${customerId}/addresses`, form)
      setForm({ label: '', address: '', is_default: false })
      loadAddresses()
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteAddress(id) {
    setError('')
    try {
      await api.del(`/customers/${customerId}/addresses/${id}`)
      loadAddresses()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-4">Delivery Addresses</h1>
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      <Card title="Add address" className="mb-4">
        <form onSubmit={addAddress} className="flex flex-col gap-3">
          <input
            className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
            placeholder="Label (e.g. Warehouse, HQ)"
            value={form.label}
            onChange={(e) => updateField('label', e.target.value)}
            required
          />
          <textarea
            className="border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400"
            placeholder="Address"
            rows={2}
            value={form.address}
            onChange={(e) => updateField('address', e.target.value)}
            required
          />
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              className="accent-yellow-500"
              checked={form.is_default}
              onChange={(e) => updateField('is_default', e.target.checked)}
            />
            Set as default
          </label>
          <button className="bg-yellow-400 hover:bg-yellow-500 text-slate-900 font-medium rounded-lg px-3 py-2 self-start">
            Add address
          </button>
        </form>
      </Card>

      <div className="flex flex-col gap-2">
        {addresses.map((a) => (
          <Card key={a.id} className="flex justify-between items-start">
            <div>
              <p className="font-medium text-slate-900 flex items-center gap-2">
                {a.label}
                {a.is_default && (
                  <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600">default</span>
                )}
              </p>
              <p className="text-sm text-gray-600">{a.address}</p>
            </div>
            <button onClick={() => deleteAddress(a.id)} className="text-red-600 hover:text-red-700 text-sm">Delete</button>
          </Card>
        ))}
        {addresses.length === 0 && <p className="text-gray-500">No addresses yet.</p>}
      </div>
    </div>
  )
}
