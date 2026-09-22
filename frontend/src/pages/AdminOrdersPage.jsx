import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import { ADMIN_INPUT, ADMIN_TABLE_WRAP, ADMIN_THEAD_TR, ADMIN_TH, ADMIN_TBODY_TR, ADMIN_TD } from '../adminStyles'

// All six statuses are listed here; the backend is the source of truth on
// which transitions are legal (app/security.py::can_transition) and simply
// rejects an illegal one with a 400 — we don't duplicate that state machine.
const STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'completed', 'cancelled']
const PAYMENT_STATUSES = ['unpaid', 'paid']

export default function AdminOrdersPage() {
  const { auth } = useAuth()
  const [orders, setOrders] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [paymentFilter, setPaymentFilter] = useState('')
  const [error, setError] = useState('')
  const [rowErrors, setRowErrors] = useState({})

  function loadOrders() {
    const params = new URLSearchParams()
    if (statusFilter) params.set('status', statusFilter)
    if (paymentFilter) params.set('payment_status', paymentFilter)
    api.get(`/orders?${params.toString()}`).then(setOrders).catch((err) => setError(err.message))
  }

  useEffect(loadOrders, [statusFilter, paymentFilter])

  async function changeStatus(orderId, status) {
    setRowErrors((prev) => ({ ...prev, [orderId]: '' }))
    try {
      await api.patch(`/orders/${orderId}/status`, { status }, { token: auth.token })
      loadOrders()
    } catch (err) {
      setRowErrors((prev) => ({ ...prev, [orderId]: err.message }))
    }
  }

  async function changePaymentStatus(orderId, payment_status) {
    setRowErrors((prev) => ({ ...prev, [orderId]: '' }))
    try {
      await api.patch(`/orders/${orderId}/payment-status`, { payment_status }, { token: auth.token })
      loadOrders()
    } catch (err) {
      setRowErrors((prev) => ({ ...prev, [orderId]: err.message }))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Orders</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Filter by status
          <select className={`${ADMIN_INPUT} w-44`} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s} className="capitalize">{s}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm text-slate-600">
          Filter by payment
          <select className={`${ADMIN_INPUT} w-40`} value={paymentFilter} onChange={(e) => setPaymentFilter(e.target.value)}>
            <option value="">All payments</option>
            {PAYMENT_STATUSES.map((s) => (
              <option key={s} value={s} className="capitalize">{s}</option>
            ))}
          </select>
        </label>
      </div>

      <div className={ADMIN_TABLE_WRAP}>
        <table className="w-full text-sm">
          <thead>
            <tr className={ADMIN_THEAD_TR}>
              <th className={ADMIN_TH}>S.No.</th>
              <th className={ADMIN_TH}>Order ID</th>
              <th className={ADMIN_TH}>Customer</th>
              <th className={ADMIN_TH}>Grand total</th>
              <th className={ADMIN_TH}>Payment</th>
              <th className={ADMIN_TH}>Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order, i) => (
              <tr key={order.id} className={`${ADMIN_TBODY_TR} align-top`}>
                <td className={ADMIN_TD}>{i + 1}</td>
                <td className={`${ADMIN_TD} font-medium text-slate-900`}>#{order.id}</td>
                <td className={ADMIN_TD}>{order.customer_name}</td>
                <td className={ADMIN_TD}>Rs. {order.grand_total.toFixed(2)}</td>
                <td className={ADMIN_TD}>
                  <select
                    className={ADMIN_INPUT}
                    value={order.payment_status}
                    disabled={order.status === 'cancelled'}
                    onChange={(e) => changePaymentStatus(order.id, e.target.value)}
                  >
                    {PAYMENT_STATUSES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </td>
                <td className={ADMIN_TD}>
                  <select
                    className={ADMIN_INPUT}
                    value={order.status}
                    onChange={(e) => changeStatus(order.id, e.target.value)}
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                  {rowErrors[order.id] && <p className="mt-1 text-xs text-red-600">{rowErrors[order.id]}</p>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {orders.length === 0 && (
          <p className="p-4 text-sm text-slate-400">
            {statusFilter || paymentFilter ? 'No orders match this filter.' : 'No orders yet.'}
          </p>
        )}
      </div>
    </div>
  )
}
