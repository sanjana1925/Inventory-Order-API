import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import AdminCard from '../components/AdminCard'

const STATUS_ORDER = ['pending', 'processing', 'shipped', 'delivered', 'completed', 'cancelled']
const STATUS_COLORS = {
  pending: 'bg-yellow-400',
  processing: 'bg-blue-400',
  shipped: 'bg-indigo-400',
  delivered: 'bg-teal-400',
  completed: 'bg-green-500',
  cancelled: 'bg-red-400',
}

function formatINR(value) {
  return `Rs. ${Math.round(value).toLocaleString('en-IN')}`
}

function formatMonth(month) {
  // "2026-03" -> "Mar"
  const [, m] = month.split('-')
  return ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][Number(m)]
}

function timeAgo(dateString) {
  const diffMs = Date.now() - new Date(dateString + 'Z').getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export default function AdminDashboardPage() {
  const { auth } = useAuth()
  const [report, setReport] = useState(null)
  const [trend, setTrend] = useState(null)
  const [topProducts, setTopProducts] = useState(null)
  const [notifications, setNotifications] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const { token } = auth
    Promise.all([
      api.get('/reports/overview', { token }),
      api.get('/reports/revenue-trend', { token }),
      api.get('/reports/top-products?limit=5', { token }),
      api.get('/notifications?audience=admin&limit=4', { token }),
    ])
      .then(([overview, revenueTrend, products, notifs]) => {
        setReport(overview)
        setTrend(revenueTrend)
        setTopProducts(products)
        setNotifications(notifs)
      })
      .catch((err) => setError(err.message))
  }, [auth])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!report || !trend || !topProducts || !notifications) return <p className="text-gray-500">Loading...</p>

  const revenueDelta =
    trend.length >= 2 && trend[trend.length - 2].revenue > 0
      ? ((trend[trend.length - 1].revenue - trend[trend.length - 2].revenue) / trend[trend.length - 2].revenue) * 100
      : null

  const stats = [
    { label: 'Total products', value: report.total_products, accent: 'bg-indigo-600' },
    { label: 'Total orders', value: report.total_orders, accent: 'bg-blue-500' },
    {
      label: 'Total revenue',
      value: formatINR(report.total_revenue),
      accent: 'bg-emerald-500',
      delta: revenueDelta === null ? null : { text: `${revenueDelta >= 0 ? '+' : ''}${revenueDelta.toFixed(1)}% vs last month`, positive: revenueDelta >= 0 },
    },
    { label: 'Low stock items', value: report.low_stock_count, accent: 'bg-red-500', highlight: report.low_stock_count > 0 },
    { label: 'Total customers', value: report.total_customers, accent: 'bg-amber-500' },
    { label: 'Units in stock', value: report.total_units.toLocaleString('en-IN'), accent: 'bg-teal-500' },
    { label: 'Inventory value', value: formatINR(report.inventory_value), accent: 'bg-violet-500' },
  ]

  const maxStatusCount = Math.max(1, ...STATUS_ORDER.map((s) => report.orders_by_status[s] || 0))
  const initials = (auth.profile.email || '??').slice(0, 2).toUpperCase()

  return (
    <div className="flex flex-col gap-7">
      <div className="flex items-center gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold text-slate-900">Admin Dashboard</h1>
          <p className="text-sm text-slate-500">Welcome back — here's what's happening across your inventory today.</p>
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-yellow-400 text-sm font-semibold text-slate-900">
          {initials}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <StatCard key={s.label} {...s} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
        <div className="flex flex-col gap-6">
          <AdminCard title="Revenue trend">
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={trend} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#EAB308" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#EAB308" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="month"
                  tickFormatter={formatMonth}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                />
                <Tooltip
                  formatter={(value) => [formatINR(value), 'Revenue']}
                  labelFormatter={formatMonth}
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                />
                <Area type="monotone" dataKey="revenue" stroke="#CA8A04" strokeWidth={2.5} fill="url(#revenueFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </AdminCard>

          <AdminCard title="Orders by status">
            <div className="flex flex-col gap-2.5">
              {STATUS_ORDER.map((status) => {
                const count = report.orders_by_status[status] || 0
                return (
                  <div key={status} className="flex items-center gap-3 text-sm">
                    <span className="w-24 shrink-0 capitalize text-slate-500">{status}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={`h-full rounded-full ${STATUS_COLORS[status]}`}
                        style={{ width: `${(count / maxStatusCount) * 100}%` }}
                      />
                    </div>
                    <span className="w-8 shrink-0 text-right font-semibold text-slate-900">{count}</span>
                  </div>
                )
              })}
            </div>
          </AdminCard>
        </div>

        <div className="flex flex-col gap-6">
          <AdminCard title="Top products">
            <div className="flex flex-col gap-3">
              {topProducts.map((p) => (
                <div key={p.id} className="flex items-center gap-3">
                  <div className="h-9 w-9 shrink-0 rounded-lg bg-slate-100" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">{p.name}</p>
                    <p className="text-xs text-slate-500">
                      {p.category} · {p.units_sold} sold
                    </p>
                  </div>
                  <p className="shrink-0 text-sm font-semibold text-slate-900">{formatINR(p.revenue)}</p>
                </div>
              ))}
              {topProducts.length === 0 && <p className="text-sm text-slate-400">No sales yet.</p>}
            </div>
          </AdminCard>

          <AdminCard title="Recent notifications">
            <div className="flex flex-col gap-3">
              {notifications.map((n) => (
                <div key={n.id} className="flex items-center gap-2.5">
                  <span className={`h-1.75 w-1.75 shrink-0 rounded-full ${n.level === 'warning' ? 'bg-amber-500' : 'bg-indigo-600'}`} />
                  <p className="min-w-0 flex-1 truncate text-sm text-slate-900">{n.message}</p>
                  <span className="shrink-0 text-xs text-slate-400">{timeAgo(n.created_at)}</span>
                </div>
              ))}
              {notifications.length === 0 && <p className="text-sm text-slate-400">No notifications yet.</p>}
            </div>
          </AdminCard>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, accent, highlight, delta }) {
  return (
    <div
      className={`rounded-xl border p-4.5 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_4px_16px_rgba(15,23,42,0.06)] ${
        highlight ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className={`h-2.25 w-2.25 rounded-full ${accent}`} />
        <p className="text-xs font-medium text-slate-500">{label}</p>
      </div>
      <p className="text-[22px] font-bold text-slate-900">{value}</p>
      {delta && (
        <span
          className={`mt-2 inline-block rounded px-1.5 py-0.5 text-[11px] font-semibold ${
            delta.positive ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
          }`}
        >
          {delta.text}
        </span>
      )}
    </div>
  )
}
