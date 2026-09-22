import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import Card from '../components/Card'

export default function FavoritesPage() {
  const { auth } = useAuth()
  const navigate = useNavigate()
  const { addToCart } = useCart()
  const [lists, setLists] = useState([])
  const [activeList, setActiveList] = useState('')
  const [favorites, setFavorites] = useState([])
  const [error, setError] = useState('')
  const [added, setAdded] = useState(0)

  function loadLists() {
    api.get(`/favorites/lists?customer_id=${auth.profile.id}`).then(setLists).catch((err) => setError(err.message))
  }

  useEffect(loadLists, [auth.profile.id])

  useEffect(() => {
    const params = new URLSearchParams({ customer_id: auth.profile.id, limit: '500' })
    if (activeList) params.set('list_name', activeList)
    api.get(`/favorites?${params.toString()}`).then(setFavorites).catch((err) => setError(err.message))
  }, [auth.profile.id, activeList])

  async function removeFavorite(id) {
    setError('')
    try {
      await api.del(`/favorites/${id}`)
      setFavorites((prev) => prev.filter((f) => f.id !== id))
      loadLists()
    } catch (err) {
      setError(err.message)
    }
  }

  async function addAllToCart() {
    setError('')
    let count = 0
    for (const fav of favorites) {
      try {
        const product = await api.get(`/products/${fav.product_id}`)
        if (product.stock_qty > 0) {
          addToCart(product, 1)
          count += 1
        }
      } catch {
        // product may have been deleted since it was favorited — skip it
      }
    }
    setAdded(count)
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-1 text-slate-900">Saved Lists</h1>
      <p className="text-sm text-slate-500 mb-4">Products you've starred from the catalog, grouped by list.</p>

      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
      {added > 0 && (
        <p className="text-green-700 text-sm mb-3">
          Added {added} item{added === 1 ? '' : 's'} to your cart.{' '}
          <button className="underline" onClick={() => navigate('/catalog')}>Go to cart / checkout</button>
        </p>
      )}

      {lists.length > 1 && (
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={() => setActiveList('')}
            className={`rounded-full px-3 py-1 text-sm font-medium ${activeList === '' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            All lists
          </button>
          {lists.map((name) => (
            <button
              key={name}
              onClick={() => setActiveList(name)}
              className={`rounded-full px-3 py-1 text-sm font-medium ${activeList === name ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              {name}
            </button>
          ))}
        </div>
      )}

      {favorites.length > 0 && (
        <button
          onClick={addAllToCart}
          className="mb-4 bg-yellow-400 hover:bg-yellow-500 text-slate-900 font-medium rounded-lg px-3.5 py-1.5 text-sm"
        >
          Add all to cart
        </button>
      )}

      <div className="flex flex-col gap-2">
        {favorites.map((f) => (
          <Card key={f.id} className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">{f.product_name}</p>
              <p className="text-xs text-slate-500">{f.list_name}</p>
            </div>
            <button onClick={() => removeFavorite(f.id)} className="text-red-600 text-sm hover:text-red-700">
              Remove
            </button>
          </Card>
        ))}
        {favorites.length === 0 && <p className="text-gray-500">No saved products yet — star items from the Catalog.</p>}
      </div>
    </div>
  )
}
