import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import AdminCard from '../components/AdminCard'
import { ADMIN_INPUT, ADMIN_BUTTON_PRIMARY, ADMIN_TABLE_WRAP, ADMIN_THEAD_TR, ADMIN_TH, ADMIN_TBODY_TR, ADMIN_TD } from '../adminStyles'

export default function AdminCategoriesPage() {
  const { auth } = useAuth()
  const [categories, setCategories] = useState([])
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  function loadCategories() {
    api.get('/categories').then(setCategories).catch((err) => setError(err.message))
  }

  useEffect(loadCategories, [])

  async function createCategory(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/categories', { name }, { token: auth.token })
      setName('')
      loadCategories()
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteCategory(id) {
    setError('')
    try {
      await api.del(`/categories/${id}`, { token: auth.token })
      loadCategories()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Categories</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <AdminCard title="Add category">
        <form onSubmit={createCategory} className="flex gap-2">
          <input
            className={`${ADMIN_INPUT} flex-1`}
            placeholder="Category name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <button className={ADMIN_BUTTON_PRIMARY}>Add</button>
        </form>
      </AdminCard>

      <div className={ADMIN_TABLE_WRAP}>
        <table className="w-full text-sm">
          <thead>
            <tr className={ADMIN_THEAD_TR}>
              <th className={ADMIN_TH}>Name</th>
              <th className={ADMIN_TH}></th>
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => (
              <tr key={c.id} className={ADMIN_TBODY_TR}>
                <td className={`${ADMIN_TD} font-medium text-slate-900`}>{c.name}</td>
                <td className={`${ADMIN_TD} text-right`}>
                  <button onClick={() => deleteCategory(c.id)} className="font-medium text-red-600 hover:text-red-700">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {categories.length === 0 && <p className="p-4 text-sm text-slate-400">No categories yet.</p>}
      </div>
    </div>
  )
}
