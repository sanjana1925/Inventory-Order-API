import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import AdminCard from '../components/AdminCard'
import { ADMIN_TABLE_WRAP, ADMIN_THEAD_TR, ADMIN_TH, ADMIN_TBODY_TR, ADMIN_TD } from '../adminStyles'

const STATUS_COLORS = {
  pending: 'bg-yellow-400',
  processing: 'bg-blue-400',
  shipped: 'bg-indigo-400',
  delivered: 'bg-teal-400',
  completed: 'bg-green-500',
  cancelled: 'bg-red-400',
}

// The dashboard page already shows /reports/overview. This page covers the
// rest of the /reports/* endpoints as a few Card sections on one screen —
// splitting each into its own route would be a lot of near-identical files
// for what is ultimately seven small read-only fetches.
export default function AdminReportsPage() {
  const { auth } = useAuth()
  const [sales, setSales] = useState(null)
  const [inventory, setInventory] = useState(null)
  const [lowStock, setLowStock] = useState([])
  const [topProducts, setTopProducts] = useState([])
  const [topCustomers, setTopCustomers] = useState([])
  const [revenueTrend, setRevenueTrend] = useState([])
  const [categoryMix, setCategoryMix] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    const opts = { token: auth.token }
    api.get('/reports/sales', opts).then(setSales).catch((err) => setError(err.message))
    api.get('/reports/inventory', opts).then(setInventory).catch((err) => setError(err.message))
    api.get('/reports/low-stock', opts).then(setLowStock).catch((err) => setError(err.message))
    api.get('/reports/top-products?limit=10', opts).then(setTopProducts).catch((err) => setError(err.message))
    api.get('/reports/top-customers?limit=10', opts).then(setTopCustomers).catch((err) => setError(err.message))
    api.get('/reports/revenue-trend', opts).then(setRevenueTrend).catch((err) => setError(err.message))
    api.get('/reports/category-mix', opts).then(setCategoryMix).catch((err) => setError(err.message))
  }, [auth.token])

  const maxStatusCount = sales ? Math.max(1, ...Object.values(sales.orders_by_status)) : 1

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {sales && (
        <AdminCard title="Sales">
          <div className="mb-4 grid grid-cols-2 gap-3">
            <StatCard label="Total orders" value={sales.total_orders} />
            <StatCard label="Total revenue" value={`Rs. ${sales.total_revenue.toFixed(2)}`} />
          </div>
          <div className="flex flex-col gap-2.5">
            {Object.entries(sales.orders_by_status).map(([status, count]) => (
              <div key={status} className="flex items-center gap-3 text-sm">
                <span className="w-24 shrink-0 capitalize text-slate-500">{status}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${STATUS_COLORS[status] || 'bg-slate-400'}`}
                    style={{ width: `${(count / maxStatusCount) * 100}%` }}
                  />
                </div>
                <span className="w-8 shrink-0 text-right font-semibold text-slate-900">{count}</span>
              </div>
            ))}
          </div>
        </AdminCard>
      )}

      {inventory && (
        <AdminCard title="Inventory">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Total products" value={inventory.total_products} />
            <StatCard label="Low stock items" value={inventory.low_stock_count} highlight={inventory.low_stock_count > 0} />
            <StatCard label="Units in stock" value={inventory.total_units} />
            <StatCard label="Inventory value" value={`Rs. ${inventory.inventory_value.toFixed(2)}`} />
          </div>
        </AdminCard>
      )}

      <AdminCard title="Low stock products">
        <SimpleTable
          rows={lowStock}
          columns={[
            { key: 'name', label: 'Name' },
            { key: 'category', label: 'Category' },
            { key: 'stock_qty', label: 'Stock' },
            { key: 'price', label: 'Price', format: (v) => `Rs. ${v.toFixed(2)}` },
          ]}
        />
      </AdminCard>

      <AdminCard title="Top products">
        <SimpleTable
          rows={topProducts}
          columns={[
            { key: 'name', label: 'Name' },
            { key: 'category', label: 'Category' },
            { key: 'units_sold', label: 'Units sold' },
            { key: 'revenue', label: 'Revenue', format: (v) => `Rs. ${v.toFixed(2)}` },
          ]}
        />
      </AdminCard>

      <AdminCard title="Top customers">
        <SimpleTable
          rows={topCustomers}
          columns={[
            { key: 'customer_name', label: 'Customer' },
            { key: 'orders', label: 'Orders' },
            { key: 'revenue', label: 'Revenue', format: (v) => `Rs. ${v.toFixed(2)}` },
          ]}
        />
      </AdminCard>

      <AdminCard title="Revenue trend">
        <SimpleTable
          rows={revenueTrend}
          columns={[
            { key: 'month', label: 'Month' },
            { key: 'orders', label: 'Orders' },
            { key: 'revenue', label: 'Revenue', format: (v) => `Rs. ${v.toFixed(2)}` },
          ]}
        />
      </AdminCard>

      <AdminCard title="Category mix">
        <SimpleTable
          rows={categoryMix}
          columns={[
            { key: 'category', label: 'Category' },
            { key: 'product_count', label: 'Products' },
            { key: 'total_units', label: 'Units' },
            { key: 'inventory_value', label: 'Value', format: (v) => `Rs. ${v.toFixed(2)}` },
          ]}
        />
      </AdminCard>
    </div>
  )
}

function StatCard({ label, value, highlight }) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-slate-50'}`}>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="text-xl font-bold text-slate-900">{value}</p>
    </div>
  )
}

// Small reusable table renderer so the seven report sections above don't
// each repeat their own <table>/<thead>/<tbody> markup.
function SimpleTable({ rows, columns }) {
  if (rows.length === 0) return <p className="text-sm text-slate-400">No data.</p>
  return (
    <div className={`${ADMIN_TABLE_WRAP} shadow-none`}>
      <table className="w-full text-sm">
        <thead>
          <tr className={ADMIN_THEAD_TR}>
            {columns.map((col) => (
              <th key={col.key} className={ADMIN_TH}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className={ADMIN_TBODY_TR}>
              {columns.map((col) => (
                <td key={col.key} className={ADMIN_TD}>
                  {col.format ? col.format(row[col.key]) : row[col.key] ?? '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
