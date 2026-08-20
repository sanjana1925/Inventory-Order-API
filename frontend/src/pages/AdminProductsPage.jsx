import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import AdminCard from '../components/AdminCard'
import { ADMIN_INPUT, ADMIN_BUTTON_PRIMARY, ADMIN_TABLE_WRAP, ADMIN_THEAD_TR, ADMIN_TH, ADMIN_TBODY_TR, ADMIN_TD } from '../adminStyles'

const LOW_STOCK_THRESHOLD = 10

export default function AdminProductsPage() {
  const { auth } = useAuth()
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')
  const [newProduct, setNewProduct] = useState({ name: '', category: '', price: '', stock_qty: '' })
  const [edits, setEdits] = useState({}) // { [productId]: { price, stock_qty } }
  const [restockDrafts, setRestockDrafts] = useState({}) // { [productId]: quantity string }
  const [restockingId, setRestockingId] = useState(null)
  const [stockFilter, setStockFilter] = useState('') // '' | 'out' | 'low' | 'in'

  function loadProducts() {
    api.get('/products?limit=1000').then(setProducts).catch((err) => setError(err.message))
  }

  useEffect(loadProducts, [])

  const visibleProducts = products.filter((p) => {
    if (stockFilter === 'out') return p.stock_qty === 0
    if (stockFilter === 'low') return p.stock_qty > 0 && p.stock_qty < LOW_STOCK_THRESHOLD
    if (stockFilter === 'in') return p.stock_qty >= LOW_STOCK_THRESHOLD
    return true
  })

  async function createProduct(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post(
        '/products',
        {
          name: newProduct.name,
          category: newProduct.category || undefined,
          price: Number(newProduct.price),
          stock_qty: Number(newProduct.stock_qty),
        },
        { token: auth.token }
      )
      setNewProduct({ name: '', category: '', price: '', stock_qty: '' })
      loadProducts()
    } catch (err) {
      setError(err.message)
    }
  }

  function startEdit(product) {
    setEdits((prev) => ({ ...prev, [product.id]: { price: product.price, stock_qty: product.stock_qty } }))
  }

  function updateEditField(productId, field, value) {
    setEdits((prev) => ({ ...prev, [productId]: { ...prev[productId], [field]: value } }))
  }

  async function saveEdit(productId) {
    setError('')
    const edit = edits[productId]
    try {
      await api.put(
        `/products/${productId}`,
        { price: Number(edit.price), stock_qty: Number(edit.stock_qty) },
        { token: auth.token }
      )
      setEdits((prev) => {
        const next = { ...prev }
        delete next[productId]
        return next
      })
      loadProducts()
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteProduct(productId) {
    setError('')
    try {
      await api.del(`/products/${productId}`, { token: auth.token })
      loadProducts()
    } catch (err) {
      setError(err.message)
    }
  }

  async function restockProduct(productId) {
    setError('')
    const quantity = Number(restockDrafts[productId])
    if (!quantity || quantity <= 0) {
      setError('Enter a restock quantity greater than 0.')
      return
    }
    setRestockingId(productId)
    try {
      // Atomic on the server (stock_qty = stock_qty + quantity in one UPDATE)
      // so this can't lose an update even if another restock or an order's
      // stock check lands at the same time.
      await api.post(`/products/${productId}/restock`, { quantity }, { token: auth.token })
      setRestockDrafts((prev) => {
        const next = { ...prev }
        delete next[productId]
        return next
      })
      loadProducts()
    } catch (err) {
      setError(err.message)
    } finally {
      setRestockingId(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Products</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <AdminCard title="Add product">
        <form onSubmit={createProduct} className="flex flex-wrap items-end gap-2">
          <input
            className={ADMIN_INPUT}
            placeholder="Name"
            value={newProduct.name}
            onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
            required
          />
          <input
            className={ADMIN_INPUT}
            placeholder="Category"
            value={newProduct.category}
            onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}
          />
          <input
            className={`${ADMIN_INPUT} w-24`}
            type="number"
            step="0.01"
            placeholder="Price"
            value={newProduct.price}
            onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
            required
          />
          <input
            className={`${ADMIN_INPUT} w-20`}
            type="number"
            placeholder="Stock"
            value={newProduct.stock_qty}
            onChange={(e) => setNewProduct({ ...newProduct, stock_qty: e.target.value })}
            required
          />
          <button className={ADMIN_BUTTON_PRIMARY}>Add</button>
        </form>
      </AdminCard>

      <label className="flex items-center gap-2 text-sm text-slate-600">
        Filter by stock
        <select className={`${ADMIN_INPUT} w-44`} value={stockFilter} onChange={(e) => setStockFilter(e.target.value)}>
          <option value="">All products</option>
          <option value="out">Out of stock</option>
          <option value="low">Low stock (&lt;{LOW_STOCK_THRESHOLD})</option>
          <option value="in">In stock</option>
        </select>
      </label>

      <div className={ADMIN_TABLE_WRAP}>
        <table className="w-full text-sm">
          <thead>
            <tr className={ADMIN_THEAD_TR}>
              <th className={ADMIN_TH}>S.No.</th>
              <th className={ADMIN_TH}>Name</th>
              <th className={ADMIN_TH}>Category</th>
              <th className={ADMIN_TH}>Price</th>
              <th className={ADMIN_TH}>Stock</th>
              <th className={ADMIN_TH}>Restock</th>
              <th className={ADMIN_TH}></th>
            </tr>
          </thead>
          <tbody>
            {visibleProducts.map((p, i) => {
              const edit = edits[p.id]
              return (
                <tr key={p.id} className={ADMIN_TBODY_TR}>
                  <td className={ADMIN_TD}>{i + 1}</td>
                  <td className={`${ADMIN_TD} font-medium text-slate-900`}>{p.name}</td>
                  <td className={ADMIN_TD}>{p.category || '-'}</td>
                  <td className={ADMIN_TD}>
                    {edit ? (
                      <input
                        type="number"
                        step="0.01"
                        className={`${ADMIN_INPUT} w-20`}
                        value={edit.price}
                        onChange={(e) => updateEditField(p.id, 'price', e.target.value)}
                      />
                    ) : (
                      `Rs. ${p.price.toFixed(2)}`
                    )}
                  </td>
                  <td className={ADMIN_TD}>
                    {edit ? (
                      <input
                        type="number"
                        className={`${ADMIN_INPUT} w-16`}
                        value={edit.stock_qty}
                        onChange={(e) => updateEditField(p.id, 'stock_qty', e.target.value)}
                      />
                    ) : (
                      <span
                        className={
                          p.stock_qty === 0
                            ? 'font-semibold text-red-600'
                            : p.stock_qty < LOW_STOCK_THRESHOLD
                              ? 'font-semibold text-amber-600'
                              : ''
                        }
                      >
                        {p.stock_qty === 0 ? 'Out of stock' : p.stock_qty}
                      </span>
                    )}
                  </td>
                  <td className={ADMIN_TD}>
                    <div className="flex items-center gap-1.5">
                      <input
                        type="number"
                        min="1"
                        placeholder="Qty"
                        className={`${ADMIN_INPUT} w-16`}
                        value={restockDrafts[p.id] ?? ''}
                        onChange={(e) => setRestockDrafts((prev) => ({ ...prev, [p.id]: e.target.value }))}
                      />
                      <button
                        disabled={restockingId === p.id}
                        onClick={() => restockProduct(p.id)}
                        className="rounded-lg bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                      >
                        + Restock
                      </button>
                    </div>
                  </td>
                  <td className={`${ADMIN_TD} text-right`}>
                    {edit ? (
                      <button onClick={() => saveEdit(p.id)} className="mr-3 font-medium text-emerald-600 hover:text-emerald-700">
                        Save
                      </button>
                    ) : (
                      <button onClick={() => startEdit(p)} className="mr-3 font-medium text-amber-700 hover:text-amber-800">
                        Edit
                      </button>
                    )}
                    <button onClick={() => deleteProduct(p.id)} className="font-medium text-red-600 hover:text-red-700">
                      Delete
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {visibleProducts.length === 0 && (
          <p className="p-4 text-sm text-slate-400">
            {products.length === 0 ? 'No products yet.' : 'No products match this filter.'}
          </p>
        )}
      </div>
    </div>
  )
}
