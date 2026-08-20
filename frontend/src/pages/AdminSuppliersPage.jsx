import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import AdminCard from '../components/AdminCard'
import { ADMIN_INPUT, ADMIN_BUTTON_PRIMARY, ADMIN_TABLE_WRAP, ADMIN_THEAD_TR, ADMIN_TH, ADMIN_TBODY_TR, ADMIN_TD } from '../adminStyles'

export default function AdminSuppliersPage() {
  const { auth } = useAuth()
  const [suppliers, setSuppliers] = useState([])
  const [error, setError] = useState('')
  const [newSupplier, setNewSupplier] = useState({ name: '', city: '', state: '' })

  function loadSuppliers() {
    api.get('/suppliers?limit=200').then(setSuppliers).catch((err) => setError(err.message))
  }

  useEffect(loadSuppliers, [])

  async function createSupplier(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post(
        '/suppliers',
        { name: newSupplier.name, city: newSupplier.city || undefined, state: newSupplier.state || undefined },
        { token: auth.token }
      )
      setNewSupplier({ name: '', city: '', state: '' })
      loadSuppliers()
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteSupplier(id) {
    setError('')
    try {
      await api.del(`/suppliers/${id}`, { token: auth.token })
      loadSuppliers()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Suppliers</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <AdminCard title="Add supplier">
        <form onSubmit={createSupplier} className="flex flex-wrap items-end gap-2">
          <input
            className={ADMIN_INPUT}
            placeholder="Name"
            value={newSupplier.name}
            onChange={(e) => setNewSupplier({ ...newSupplier, name: e.target.value })}
            required
          />
          <input
            className={ADMIN_INPUT}
            placeholder="City"
            value={newSupplier.city}
            onChange={(e) => setNewSupplier({ ...newSupplier, city: e.target.value })}
          />
          <input
            className={ADMIN_INPUT}
            placeholder="State"
            value={newSupplier.state}
            onChange={(e) => setNewSupplier({ ...newSupplier, state: e.target.value })}
          />
          <button className={ADMIN_BUTTON_PRIMARY}>Add</button>
        </form>
      </AdminCard>

      <div className={ADMIN_TABLE_WRAP}>
        <table className="w-full text-sm">
          <thead>
            <tr className={ADMIN_THEAD_TR}>
              <th className={ADMIN_TH}>Name</th>
              <th className={ADMIN_TH}>City</th>
              <th className={ADMIN_TH}>State</th>
              <th className={ADMIN_TH}></th>
            </tr>
          </thead>
          <tbody>
            {suppliers.map((s) => (
              <tr key={s.id} className={ADMIN_TBODY_TR}>
                <td className={`${ADMIN_TD} font-medium text-slate-900`}>{s.name}</td>
                <td className={ADMIN_TD}>{s.city || '-'}</td>
                <td className={ADMIN_TD}>{s.state || '-'}</td>
                <td className={`${ADMIN_TD} text-right`}>
                  <button onClick={() => deleteSupplier(s.id)} className="font-medium text-red-600 hover:text-red-700">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {suppliers.length === 0 && <p className="p-4 text-sm text-slate-400">No suppliers yet.</p>}
      </div>
    </div>
  )
}
