import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import AdminCard from '../components/AdminCard'
import { ADMIN_INPUT, ADMIN_BUTTON_PRIMARY, ADMIN_TABLE_WRAP, ADMIN_THEAD_TR, ADMIN_TH, ADMIN_TBODY_TR, ADMIN_TD } from '../adminStyles'

export default function AdminUsersPage() {
  const { auth } = useAuth()
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const [form, setForm] = useState({ email: '', password: '', role: 'staff' })

  function loadUsers() {
    api.get('/users', { token: auth.token }).then(setUsers).catch((err) => setError(err.message))
  }

  useEffect(loadUsers, [auth.token])

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function createUser(e) {
    e.preventDefault()
    setError('')
    try {
      // No token needed here on purpose — POST /users is the bootstrap route
      // used to create the very first admin account before anyone can log in.
      await api.post('/users', form)
      setForm({ email: '', password: '', role: 'staff' })
      loadUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteUser(id) {
    setError('')
    try {
      await api.del(`/users/${id}`, { token: auth.token })
      loadUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Users</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <AdminCard title="Add admin/staff user">
        <form onSubmit={createUser} className="flex flex-wrap items-end gap-2">
          <input
            className={ADMIN_INPUT}
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(e) => updateField('email', e.target.value)}
            required
          />
          <input
            className={ADMIN_INPUT}
            type="password"
            placeholder="Password"
            minLength={6}
            value={form.password}
            onChange={(e) => updateField('password', e.target.value)}
            required
          />
          <select className={ADMIN_INPUT} value={form.role} onChange={(e) => updateField('role', e.target.value)}>
            <option value="staff">staff</option>
            <option value="admin">admin</option>
          </select>
          <button className={ADMIN_BUTTON_PRIMARY}>Add</button>
        </form>
      </AdminCard>

      <div className={ADMIN_TABLE_WRAP}>
        <table className="w-full text-sm">
          <thead>
            <tr className={ADMIN_THEAD_TR}>
              <th className={ADMIN_TH}>Email</th>
              <th className={ADMIN_TH}>Role</th>
              <th className={ADMIN_TH}></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className={ADMIN_TBODY_TR}>
                <td className={`${ADMIN_TD} font-medium text-slate-900`}>{u.email}</td>
                <td className={`${ADMIN_TD} capitalize`}>{u.role}</td>
                <td className={`${ADMIN_TD} text-right`}>
                  <button onClick={() => deleteUser(u.id)} className="font-medium text-red-600 hover:text-red-700">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <p className="p-4 text-sm text-slate-400">No users yet.</p>}
      </div>
    </div>
  )
}
