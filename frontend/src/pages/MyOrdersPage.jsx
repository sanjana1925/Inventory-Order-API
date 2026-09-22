import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, API_BASE } from '../api'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import Card from '../components/Card'

const STATUS_BADGE = {
  pending: 'bg-yellow-50 text-yellow-700',
  processing: 'bg-blue-50 text-blue-600',
  shipped: 'bg-indigo-50 text-indigo-600',
  delivered: 'bg-teal-50 text-teal-600',
  completed: 'bg-emerald-50 text-emerald-600',
  cancelled: 'bg-red-50 text-red-600',
}
const PAYMENT_BADGE = {
  unpaid: 'bg-slate-100 text-slate-600',
  paid: 'bg-emerald-50 text-emerald-600',
}

export default function MyOrdersPage() {
  const { auth } = useAuth()
  const navigate = useNavigate()
  const { addToCart } = useCart()
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [reorderNote, setReorderNote] = useState('')

  function loadOrders() {
    api
      .get(`/orders?customer_id=${auth.profile.id}`)
      .then(setOrders)
      .catch((err) => setError(err.message))
  }

  useEffect(loadOrders, [auth.profile.id])

  async function payNow(orderId) {
    setBusyId(orderId)
    setError('')
    try {
      await api.post(`/orders/${orderId}/pay`)
      loadOrders()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  async function cancelOrder(orderId) {
    setBusyId(orderId)
    setError('')
    try {
      await api.post(`/orders/${orderId}/cancel`)
      loadOrders()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  // Re-adds each line at *current* price/stock (not the historical unit_price
  // on the order) — a stale/deleted product or one now out of stock is
  // skipped rather than failing the whole reorder.
  async function buyAgain(order) {
    setBusyId(order.id)
    setError('')
    setReorderNote('')
    let added = 0
    let skipped = 0
    for (const item of order.items) {
      try {
        const product = await api.get(`/products/${item.product_id}`)
        // addToCart clamps to current stock itself (accounting for whatever
        // is already in the cart) — no need to pre-compute the cap here.
        if (addToCart(product, item.quantity) > 0) {
          added += 1
        } else {
          skipped += 1
        }
      } catch {
        skipped += 1
      }
    }
    setBusyId(null)
    if (added > 0) {
      setReorderNote(
        `Added ${added} item${added === 1 ? '' : 's'} to your cart${skipped > 0 ? ` (${skipped} unavailable and skipped)` : ''}.`
      )
    } else {
      setError('None of the items on this order are available to reorder right now.')
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-3 text-slate-900">My Orders</h1>
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
      {reorderNote && (
        <p className="text-green-700 text-sm mb-3">
          {reorderNote} <button className="underline" onClick={() => navigate('/catalog')}>Go to cart / checkout</button>
        </p>
      )}
      <div className="flex flex-col gap-3">
        {orders.map((order) => (
          <Card key={order.id}>
            <div className="flex justify-between items-start">
              <div>
                <p className="font-medium text-slate-900">Order #{order.id}</p>
                <p className="text-sm text-gray-500">{new Date(order.created_at).toLocaleString()}</p>
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <p className="font-medium text-slate-900">Rs. {order.grand_total.toFixed(2)}</p>
                <div className="flex gap-1.5">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_BADGE[order.status] || 'bg-slate-100 text-slate-600'}`}>
                    {order.status}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${PAYMENT_BADGE[order.payment_status] || 'bg-slate-100 text-slate-600'}`}>
                    {order.payment_status}
                  </span>
                </div>
              </div>
            </div>

            <ul className="text-sm text-gray-600 mt-2 list-disc list-inside">
              {order.items.map((item) => (
                <li key={item.product_id}>
                  {item.product_name} x {item.quantity} = Rs. {item.line_total.toFixed(2)}
                </li>
              ))}
            </ul>

            <div className="flex gap-2 mt-3 text-sm">
              {order.payment_status === 'unpaid' && order.status !== 'cancelled' && (
                <button
                  disabled={busyId === order.id}
                  onClick={() => payNow(order.id)}
                  className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded px-3 py-1"
                >
                  Pay now (simulated)
                </button>
              )}
              {order.status === 'pending' && (
                <button
                  disabled={busyId === order.id}
                  onClick={() => cancelOrder(order.id)}
                  className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded px-3 py-1"
                >
                  Cancel
                </button>
              )}
              <a
                href={`${API_BASE}/orders/${order.id}/invoice`}
                target="_blank"
                rel="noreferrer"
                className="border rounded px-3 py-1 hover:bg-gray-50"
              >
                Download invoice
              </a>
              <button
                disabled={busyId === order.id}
                onClick={() => buyAgain(order)}
                className="bg-yellow-400 hover:bg-yellow-500 disabled:opacity-50 text-slate-900 font-medium rounded px-3 py-1"
              >
                Buy it again
              </button>
            </div>
          </Card>
        ))}
        {orders.length === 0 && <p className="text-gray-500">No orders yet.</p>}
      </div>
    </div>
  )
}
