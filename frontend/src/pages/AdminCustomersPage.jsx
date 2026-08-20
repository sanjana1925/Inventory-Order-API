import { useEffect, useState } from 'react'
import { api } from '../api'
import { ADMIN_INPUT, ADMIN_TABLE_WRAP, ADMIN_THEAD_TR, ADMIN_TH, ADMIN_TBODY_TR, ADMIN_TD } from '../adminStyles'

export default function AdminCustomersPage() {
  const [customers, setCustomers] = useState([])
  const [q, setQ] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    const params = new URLSearchParams({ limit: '1000' })
    if (q) params.set('q', q)
    api.get(`/customers?${params.toString()}`).then(setCustomers).catch((err) => setError(err.message))
  }, [q])

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Customers</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <input
        className={`${ADMIN_INPUT} max-w-sm`}
        placeholder="Search by name or email..."
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      <div className={ADMIN_TABLE_WRAP}>
        <table className="w-full text-sm">
          <thead>
            <tr className={ADMIN_THEAD_TR}>
              <th className={ADMIN_TH}>S.No.</th>
              <th className={ADMIN_TH}>Name</th>
              <th className={ADMIN_TH}>Email</th>
              <th className={ADMIN_TH}>Phone</th>
              <th className={ADMIN_TH}>Address</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c, i) => (
              <tr key={c.id} className={ADMIN_TBODY_TR}>
                <td className={ADMIN_TD}>{i + 1}</td>
                <td className={`${ADMIN_TD} font-medium text-slate-900`}>{c.name}</td>
                <td className={ADMIN_TD}>
                  <a href={`mailto:${c.email}`} className="text-amber-700 hover:text-amber-800">{c.email}</a>
                </td>
                <td className={ADMIN_TD}>{c.phone || '-'}</td>
                <td className={ADMIN_TD}>{c.address || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {customers.length === 0 && <p className="p-4 text-sm text-slate-400">No customers yet.</p>}
      </div>
    </div>
  )
}
