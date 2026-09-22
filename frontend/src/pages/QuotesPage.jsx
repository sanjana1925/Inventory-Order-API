import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import Card from '../components/Card'
import { ADMIN_INPUT, ADMIN_BUTTON_PRIMARY } from '../adminStyles'

const STATUS_BADGE = {
  requested: 'bg-yellow-50 text-yellow-700',
  quoted: 'bg-blue-50 text-blue-600',
  rejected: 'bg-red-50 text-red-600',
  converted: 'bg-emerald-50 text-emerald-600',
}

// One page covers both /quotes (customer) and /admin/quotes (staff) — the
// two views share the same data shape and differ only in which actions are
// shown, so branching on auth.role here is simpler than two near-duplicate files.
export default function QuotesPage() {
  const { auth } = useAuth()
  const isStaff = auth.role === 'staff'
  const [quotes, setQuotes] = useState([])
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  // customer-only: request-a-quote form
  const [lines, setLines] = useState([{ product_id: '', quantity: 1 }])

  // staff-only: draft prices being entered per quote, keyed by quote id then product id
  const [priceDrafts, setPriceDrafts] = useState({})

  function loadQuotes() {
    const path = isStaff ? '/quotes' : `/quotes?customer_id=${auth.profile.id}`
    api.get(path).then(setQuotes).catch((err) => setError(err.message))
  }

  useEffect(loadQuotes, [isStaff, auth.profile.id])

  useEffect(() => {
    if (!isStaff) {
      api.get('/products').then(setProducts).catch(() => {})
    }
  }, [isStaff])

  function updateLine(index, field, value) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, [field]: value } : line)))
  }

  function addLine() {
    setLines((prev) => [...prev, { product_id: '', quantity: 1 }])
  }

  function removeLine(index) {
    setLines((prev) => prev.filter((_, i) => i !== index))
  }

  async function requestQuote(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/quotes', {
        customer_name: auth.profile.name,
        customer_id: auth.profile.id,
        items: lines.map((line) => ({ product_id: Number(line.product_id), quantity: Number(line.quantity) })),
      })
      setLines([{ product_id: '', quantity: 1 }])
      loadQuotes()
    } catch (err) {
      setError(err.message)
    }
  }

  function setDraftPrice(quoteId, productId, price) {
    setPriceDrafts((prev) => ({
      ...prev,
      [quoteId]: { ...prev[quoteId], [productId]: price },
    }))
  }

  async function submitPrices(quote) {
    setBusyId(quote.id)
    setError('')
    try {
      const draft = priceDrafts[quote.id] || {}
      await api.patch(
        `/quotes/${quote.id}/price`,
        { items: quote.items.map((item) => ({ product_id: item.product_id, quoted_unit_price: Number(draft[item.product_id]) })) },
        { token: auth.token }
      )
      loadQuotes()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  async function rejectQuote(id) {
    setBusyId(id)
    setError('')
    try {
      await api.post(`/quotes/${id}/reject`, undefined, { token: auth.token })
      loadQuotes()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  async function convertQuote(id) {
    setBusyId(id)
    setError('')
    try {
      await api.post(`/quotes/${id}/convert`)
      loadQuotes()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-4">Quotes</h1>
      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      {!isStaff && (
        <Card title="Request a quote" className="mb-4">
          <form onSubmit={requestQuote} className="flex flex-col gap-3">
            {lines.map((line, i) => (
              <div key={i} className="flex gap-2 items-center">
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
                {lines.length > 1 && (
                  <button type="button" onClick={() => removeLine(i)} className="text-red-500 hover:text-red-600">x</button>
                )}
              </div>
            ))}
            <div className="flex gap-2">
              <button type="button" onClick={addLine} className="border border-slate-300 rounded-lg px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100">
                + Add line
              </button>
              <button className={ADMIN_BUTTON_PRIMARY}>Request quote</button>
            </div>
          </form>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {quotes.map((quote) => (
          <Card key={quote.id}>
            <div className="flex justify-between items-start">
              <div>
                <p className="font-medium text-slate-900">
                  Quote #{quote.id}{isStaff ? ` · ${quote.customer_name}` : ''}
                </p>
                <p className="text-sm text-gray-500">{new Date(quote.created_at).toLocaleString()}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_BADGE[quote.status] || 'bg-slate-100 text-slate-600'}`}>
                {quote.status}
              </span>
            </div>

            <ul className="text-sm text-gray-600 mt-2 flex flex-col gap-1">
              {quote.items.map((item) => (
                <li key={item.product_id} className="flex items-center gap-2">
                  <span className="flex-1">{item.product_name} x {item.quantity}</span>
                  {isStaff && quote.status === 'requested' ? (
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="Unit price"
                      className={`${ADMIN_INPUT} w-24`}
                      value={(priceDrafts[quote.id] || {})[item.product_id] ?? ''}
                      onChange={(e) => setDraftPrice(quote.id, item.product_id, e.target.value)}
                    />
                  ) : (
                    item.quoted_unit_price != null && <span>Rs. {item.quoted_unit_price.toFixed(2)}</span>
                  )}
                </li>
              ))}
            </ul>

            {quote.order_id && (
              <p className="text-sm text-green-700 mt-2">Converted to order #{quote.order_id}</p>
            )}

            <div className="flex gap-2 mt-3 text-sm">
              {isStaff && quote.status === 'requested' && (
                <>
                  <button
                    disabled={busyId === quote.id}
                    onClick={() => submitPrices(quote)}
                    className={ADMIN_BUTTON_PRIMARY}
                  >
                    Submit prices
                  </button>
                  <button
                    disabled={busyId === quote.id}
                    onClick={() => rejectQuote(quote.id)}
                    className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg px-3.5 py-1.5 text-sm font-medium"
                  >
                    Reject
                  </button>
                </>
              )}
              {quote.status === 'quoted' && (
                <button
                  disabled={busyId === quote.id}
                  onClick={() => convertQuote(quote.id)}
                  className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded px-3 py-1"
                >
                  Convert to order
                </button>
              )}
            </div>
          </Card>
        ))}
        {quotes.length === 0 && <p className="text-gray-500">No quotes yet.</p>}
      </div>
    </div>
  )
}
