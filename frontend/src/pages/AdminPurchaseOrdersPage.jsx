import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import AdminCard from '../components/AdminCard'
import { ADMIN_INPUT, ADMIN_BUTTON_PRIMARY, ADMIN_BUTTON_SECONDARY } from '../adminStyles'

const STATUS_BADGE = {
  draft: 'bg-slate-100 text-slate-600',
  ordered: 'bg-blue-50 text-blue-600',
  received: 'bg-emerald-50 text-emerald-600',
}

export default function AdminPurchaseOrdersPage() {
  const { auth } = useAuth()
  const [orders, setOrders] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const [supplierId, setSupplierId] = useState('')
  const [lines, setLines] = useState([{ product_id: '', quantity: 1, unit_cost: '' }])

  function loadOrders() {
    api.get('/purchase-orders', { token: auth.token }).then(setOrders).catch((err) => setError(err.message))
  }

  useEffect(loadOrders, [auth.token])

  useEffect(() => {
    api.get('/suppliers?limit=200').then(setSuppliers).catch(() => {})
    api.get('/products').then(setProducts).catch(() => {})
  }, [])

  function updateLine(index, field, value) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, [field]: value } : line)))
  }

  function addLine() {
    setLines((prev) => [...prev, { product_id: '', quantity: 1, unit_cost: '' }])
  }

  function removeLine(index) {
    setLines((prev) => prev.filter((_, i) => i !== index))
  }

  async function createOrder(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post(
        '/purchase-orders',
        {
          supplier_id: Number(supplierId),
          items: lines.map((line) => ({
            product_id: Number(line.product_id),
            quantity: Number(line.quantity),
            unit_cost: Number(line.unit_cost),
          })),
        },
        { token: auth.token }
      )
      setSupplierId('')
      setLines([{ product_id: '', quantity: 1, unit_cost: '' }])
      loadOrders()
    } catch (err) {
      setError(err.message)
    }
  }

  async function receiveOrder(id) {
    setBusyId(id)
    setError('')
    try {
      await api.post(`/purchase-orders/${id}/receive`, undefined, { token: auth.token })
      loadOrders()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Purchase Orders</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <AdminCard title="Create purchase order">
        <form onSubmit={createOrder} className="flex flex-col gap-3">
          <select
            className={`${ADMIN_INPUT} w-64`}
            value={supplierId}
            onChange={(e) => setSupplierId(e.target.value)}
            required
          >
            <option value="">Select supplier...</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          {lines.map((line, i) => (
            <div key={i} className="flex items-center gap-2">
              <select
                className={`${ADMIN_INPUT} flex-1`}
                value={line.product_id}
                onChange={(e) => updateLine(i, 'product_id', e.target.value)}
                required
              >
                <option value="">Select product...</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <input
                type="number"
                min="1"
                className={`${ADMIN_INPUT} w-20`}
                placeholder="Qty"
                value={line.quantity}
                onChange={(e) => updateLine(i, 'quantity', e.target.value)}
                required
              />
              <input
                type="number"
                step="0.01"
                min="0"
                className={`${ADMIN_INPUT} w-24`}
                placeholder="Unit cost"
                value={line.unit_cost}
                onChange={(e) => updateLine(i, 'unit_cost', e.target.value)}
                required
              />
              {lines.length > 1 && (
                <button type="button" onClick={() => removeLine(i)} className="text-red-500 hover:text-red-600">
                  x
                </button>
              )}
            </div>
          ))}

          <div className="flex gap-2">
            <button type="button" onClick={addLine} className={ADMIN_BUTTON_SECONDARY}>
              + Add line
            </button>
            <button className={ADMIN_BUTTON_PRIMARY}>Create purchase order</button>
          </div>
        </form>
      </AdminCard>

      <div className="flex flex-col gap-3">
        {orders.map((po) => (
          <AdminCard key={po.id}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-slate-900">PO #{po.id} &middot; {po.supplier_name}</p>
                <p className="text-sm text-slate-500">{new Date(po.created_at).toLocaleString()}</p>
              </div>
              <div className="text-right">
                <p className="font-medium text-slate-900">Rs. {po.total_cost.toFixed(2)}</p>
                <span
                  className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                    STATUS_BADGE[po.status] || 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {po.status}
                </span>
              </div>
            </div>
            <ul className="mt-3 flex flex-col gap-1 text-sm text-slate-600">
              {po.items.map((item) => (
                <li key={item.product_id}>
                  {item.product_name} x {item.quantity} @ Rs. {item.unit_cost.toFixed(2)}
                </li>
              ))}
            </ul>
            {po.status === 'ordered' && (
              <button
                disabled={busyId === po.id}
                onClick={() => receiveOrder(po.id)}
                className="mt-3 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Receive
              </button>
            )}
          </AdminCard>
        ))}
        {orders.length === 0 && <p className="text-sm text-slate-400">No purchase orders yet.</p>}
      </div>
    </div>
  )
}
