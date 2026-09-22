import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import Card from '../components/Card'

// The API has no product image field — these are generated placeholder art
// (category-tinted gradient + icon) rather than a fake image URL pointing
// nowhere, so the catalog grid reads as lively without faking real photos.
const CATEGORY_STYLE = {
  'Home Appliances': { gradient: 'from-sky-400 to-blue-500', icon: '🔌' },
  Furniture: { gradient: 'from-amber-400 to-orange-500', icon: '🛋️' },
  'Mobile Appliances': { gradient: 'from-violet-400 to-purple-500', icon: '📱' },
  'Home Decor': { gradient: 'from-rose-400 to-pink-500', icon: '🖼️' },
}
const DEFAULT_CATEGORY_STYLE = { gradient: 'from-slate-300 to-slate-400', icon: '📦' }

function ProductImage({ category }) {
  const style = CATEGORY_STYLE[category] || DEFAULT_CATEGORY_STYLE
  return (
    <div className={`flex h-28 shrink-0 items-center justify-center rounded-t-xl bg-linear-to-br ${style.gradient} text-4xl`}>
      {style.icon}
    </div>
  )
}

const SORT_OPTIONS = [
  { value: 'id', label: 'Default' },
  { value: 'name', label: 'Name (A-Z)' },
  { value: 'price_asc', label: 'Price: Low to High' },
  { value: 'price_desc', label: 'Price: High to Low' },
  { value: 'stock_desc', label: 'Stock: Most available' },
]
const INPUT = 'border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400'

export default function CatalogPage() {
  const { auth } = useAuth()
  const navigate = useNavigate()
  const { cart, addToCart, setQuantity, removeFromCart, clearCart, cartTotal } = useCart()
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [inStockOnly, setInStockOnly] = useState(false)
  const [sort, setSort] = useState('id')
  const [error, setError] = useState('')
  const [placing, setPlacing] = useState(false)
  const [placedOrderId, setPlacedOrderId] = useState(null)

  // favoriteId keyed by product_id, for the default "Favorites" list — lets
  // the star toggle know whether to POST (add) or DELETE (remove).
  const [favoriteIds, setFavoriteIds] = useState({})

  useEffect(() => {
    api.get('/products/categories').then(setCategories).catch(() => {})
  }, [])

  useEffect(() => {
    api
      .get(`/favorites?customer_id=${auth.profile.id}&list_name=${encodeURIComponent('Favorites')}&limit=500`)
      .then((rows) => {
        const map = {}
        rows.forEach((f) => { map[f.product_id] = f.id })
        setFavoriteIds(map)
      })
      .catch(() => {})
  }, [auth.profile.id])

  useEffect(() => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (category) params.set('category', category)
    if (minPrice) params.set('min_price', minPrice)
    if (maxPrice) params.set('max_price', maxPrice)
    if (inStockOnly) params.set('in_stock_only', 'true')
    params.set('sort', sort)
    api
      .get(`/products?${params.toString()}`)
      .then(setProducts)
      .catch((err) => setError(err.message))
  }, [q, category, minPrice, maxPrice, inStockOnly, sort])

  async function toggleFavorite(product) {
    const existingId = favoriteIds[product.id]
    try {
      if (existingId) {
        await api.del(`/favorites/${existingId}`)
        setFavoriteIds((prev) => {
          const next = { ...prev }
          delete next[product.id]
          return next
        })
      } else {
        const favorite = await api.post('/favorites', { customer_id: auth.profile.id, product_id: product.id })
        setFavoriteIds((prev) => ({ ...prev, [product.id]: favorite.id }))
      }
    } catch (err) {
      setError(err.message)
    }
  }

  async function placeOrder() {
    setError('')
    setPlacing(true)
    setPlacedOrderId(null)
    try {
      const order = await api.post('/orders', {
        customer_name: auth.profile.name,
        customer_id: auth.profile.id,
        items: cart.map((line) => ({ product_id: line.product.id, quantity: line.quantity })),
      })
      clearCart()
      setPlacedOrderId(order.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setPlacing(false)
    }
  }

  return (
    <div className="grid grid-cols-3 gap-4 items-start">
      <div className="col-span-2">
        <h1 className="text-xl font-semibold mb-3 text-slate-900">Catalog</h1>

        <div className="flex flex-wrap gap-2 mb-4">
          <input
            className={`${INPUT} flex-1 min-w-45`}
            placeholder="Search products..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select className={INPUT} value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select className={INPUT} value={sort} onChange={(e) => setSort(e.target.value)}>
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <input
            type="number"
            min="0"
            className={`${INPUT} w-24`}
            placeholder="Min Rs."
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
          />
          <input
            type="number"
            min="0"
            className={`${INPUT} w-24`}
            placeholder="Max Rs."
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
          />
          <label className="flex items-center gap-1.5 text-sm text-slate-600 border border-slate-300 rounded-lg px-3">
            <input type="checkbox" className="accent-yellow-500" checked={inStockOnly} onChange={(e) => setInStockOnly(e.target.checked)} />
            In stock only
          </label>
        </div>

        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

        <div className="grid grid-cols-2 gap-3">
          {products.map((p) => (
            <div
              key={p.id}
              className="relative flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_1px_3px_rgba(15,23,42,0.04),0_4px_16px_rgba(15,23,42,0.06)]"
            >
              <ProductImage category={p.category} />
              <button
                onClick={() => toggleFavorite(p)}
                title={favoriteIds[p.id] ? 'Remove from favorites' : 'Save to favorites'}
                className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-white/90 text-base shadow hover:bg-white"
              >
                {favoriteIds[p.id] ? '⭐' : '☆'}
              </button>
              <div className="flex flex-1 flex-col gap-1 p-3">
                <span className="font-medium text-slate-900">{p.name}</span>
                <span className="text-sm text-slate-500">{p.category || 'Uncategorized'}</span>
                <span className="text-sm text-slate-700">
                  Rs. {p.price.toFixed(2)} &middot; {p.stock_qty} in stock
                </span>
                {(() => {
                  const inCart = cart.find((line) => line.product.id === p.id)?.quantity || 0
                  const atCap = p.stock_qty > 0 && inCart >= p.stock_qty
                  return (
                    <button
                      disabled={p.stock_qty === 0 || atCap}
                      onClick={() => {
                        if (addToCart(p) === 0) setError(`Only ${p.stock_qty} of "${p.name}" in stock — already in your cart.`)
                      }}
                      className="mt-auto pt-2 bg-yellow-400 hover:bg-yellow-500 disabled:bg-slate-100 disabled:text-slate-400 text-slate-900 rounded-lg px-3 py-1.5 text-sm font-medium self-start"
                    >
                      {p.stock_qty === 0 ? 'Out of stock' : atCap ? 'Max in cart' : 'Add to cart'}
                    </button>
                  )
                })()}
              </div>
            </div>
          ))}
          {products.length === 0 && <p className="text-gray-500 col-span-2">No products found.</p>}
        </div>
      </div>

      <div className="sticky top-4 self-start">
        <Card>
          <h2 className="font-semibold mb-3 text-slate-900">Cart</h2>
          {cart.length === 0 && <p className="text-sm text-gray-500">Cart is empty.</p>}
          {cart.map((line) => (
            <div key={line.product.id} className="flex items-center gap-2 mb-2 text-sm">
              <span className="flex-1">{line.product.name}</span>
              <input
                type="number"
                min="1"
                max={line.product.stock_qty}
                value={line.quantity}
                onChange={(e) => setQuantity(line.product.id, e.target.value)}
                className="border rounded w-14 px-1 py-0.5"
              />
              <button onClick={() => removeFromCart(line.product.id)} className="text-red-600">x</button>
            </div>
          ))}
          {cart.length > 0 && (
            <>
              <div className="border-t pt-2 mt-2 font-medium">Total: Rs. {cartTotal.toFixed(2)}</div>
              <button
                onClick={placeOrder}
                disabled={placing}
                className="mt-3 w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded px-3 py-2"
              >
                {placing ? 'Placing order...' : 'Place order'}
              </button>
            </>
          )}
          {placedOrderId && (
            <p className="text-green-700 text-sm mt-3">
              Order #{placedOrderId} placed.{' '}
              <button className="underline" onClick={() => navigate('/my-orders')}>View my orders</button>
            </p>
          )}
        </Card>
      </div>
    </div>
  )
}
