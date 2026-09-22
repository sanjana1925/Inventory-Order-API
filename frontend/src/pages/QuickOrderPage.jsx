import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useCart } from '../context/CartContext'
import Card from '../components/Card'

const INPUT = 'border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400'

// The one-shot bulk-add form for buyers who already know what they want by
// name/SKU and quantity, instead of browsing the catalog product-by-product.
export default function QuickOrderPage() {
  const navigate = useNavigate()
  const { addToCart } = useCart()
  const [products, setProducts] = useState([])
  const [rows, setRows] = useState([{ productId: '', quantity: 1 }])
  const [error, setError] = useState('')
  const [added, setAdded] = useState(0)

  useEffect(() => {
    api.get('/products?limit=1000').then(setProducts).catch((err) => setError(err.message))
  }, [])

  function updateRow(index, field, value) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
    setAdded(0)
  }

  function addRow() {
    setRows((prev) => [...prev, { productId: '', quantity: 1 }])
  }

  function removeRow(index) {
    setRows((prev) => prev.filter((_, i) => i !== index))
  }

  function addAllToCart(e) {
    e.preventDefault()
    setError('')
    const productsById = new Map(products.map((p) => [String(p.id), p]))
    const problems = []
    let count = 0

    for (const row of rows) {
      if (!row.productId) continue
      const product = productsById.get(String(row.productId))
      const quantity = Number(row.quantity)
      if (!product) continue
      if (quantity < 1) continue

      // addToCart clamps to current stock minus whatever's already in the
      // cart and reports back how much it actually added — that's the
      // single source of truth for the cap, not a duplicate check here.
      const added = addToCart(product, quantity)
      if (added < quantity) {
        problems.push(`${product.name}: only ${added} added (stock limit reached)`)
      }
      if (added > 0) count += 1
    }

    if (problems.length > 0) {
      setError(problems.join('; '))
    }
    if (count > 0) {
      setAdded(count)
      setRows([{ productId: '', quantity: 1 }])
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-semibold mb-1 text-slate-900">Quick Order</h1>
      <p className="text-sm text-slate-500 mb-4">
        Know what you need? Add multiple products by name and quantity in one pass, then check out from the cart.
      </p>

      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
      {added > 0 && (
        <p className="text-green-700 text-sm mb-3">
          Added {added} line{added === 1 ? '' : 's'} to your cart.{' '}
          <button className="underline" onClick={() => navigate('/catalog')}>Go to cart / checkout</button>
        </p>
      )}

      <Card>
        <form onSubmit={addAllToCart} className="flex flex-col gap-2">
          {rows.map((row, i) => {
            const product = products.find((p) => String(p.id) === String(row.productId))
            return (
              <div key={i} className="flex items-center gap-2">
                <select
                  className={`${INPUT} flex-1`}
                  value={row.productId}
                  onChange={(e) => updateRow(i, 'productId', e.target.value)}
                >
                  <option value="">Select product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id} disabled={p.stock_qty === 0}>
                      {p.name}{p.stock_qty === 0 ? ' (out of stock)' : ''}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min="1"
                  max={product?.stock_qty}
                  className={`${INPUT} w-20`}
                  value={row.quantity}
                  onChange={(e) => updateRow(i, 'quantity', e.target.value)}
                />
                <span className="w-28 shrink-0 text-sm text-slate-500">
                  {product ? `Rs. ${product.price.toFixed(2)}` : ''}
                </span>
                {rows.length > 1 && (
                  <button type="button" onClick={() => removeRow(i)} className="text-red-500 hover:text-red-600">
                    x
                  </button>
                )}
              </div>
            )
          })}

          <div className="flex gap-2 mt-2">
            <button
              type="button"
              onClick={addRow}
              className="border border-slate-300 rounded-lg px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              + Add row
            </button>
            <button className="bg-yellow-400 hover:bg-yellow-500 text-slate-900 font-medium rounded-lg px-3.5 py-1.5 text-sm">
              Add all to cart
            </button>
          </div>
        </form>
      </Card>
    </div>
  )
}
