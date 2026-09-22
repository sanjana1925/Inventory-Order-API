import { createContext, useContext, useState } from 'react'

const CartContext = createContext(null)

// In-memory only, not persisted — same reasoning as the cart that used to
// live inside CatalogPage alone. Lifted to context so Quick Order and
// "Buy it again" (MyOrdersPage) can add to the same cart the Catalog page
// checks out from.
//
// Client-side stock clamping here is a UX nicety only — it lets a shopper
// know immediately they've hit the limit instead of finding out at checkout.
// The real correctness guarantee is server-side: POST /orders re-validates
// every line's stock against the database, inside one transaction, before
// writing anything (see app/routers/orders.py) — so a stale/bypassed client
// check can never cause an oversell.
export function CartProvider({ children }) {
  const [cart, setCart] = useState([]) // [{ product, quantity }]

  // Returns how many units were actually added (may be less than requested,
  // or 0, if the line was already at the product's current stock cap).
  function addToCart(product, quantity = 1) {
    const existing = cart.find((line) => line.product.id === product.id)
    const currentQty = existing ? existing.quantity : 0
    const capped = Math.max(0, Math.min(currentQty + quantity, product.stock_qty))
    const actuallyAdded = capped - currentQty
    if (actuallyAdded <= 0) return 0

    setCart((prev) => {
      const stillExisting = prev.find((line) => line.product.id === product.id)
      if (stillExisting) {
        // Refresh the stored product too, in case stock/price changed since
        // this line was first added.
        return prev.map((line) => (line.product.id === product.id ? { ...line, product, quantity: capped } : line))
      }
      return [...prev, { product, quantity: capped }]
    })
    return actuallyAdded
  }

  function setQuantity(productId, quantity) {
    setCart((prev) =>
      prev
        .map((line) => {
          if (line.product.id !== productId) return line
          const capped = Math.min(Math.max(0, Number(quantity) || 0), line.product.stock_qty)
          return { ...line, quantity: capped }
        })
        .filter((line) => line.quantity > 0)
    )
  }

  function removeFromCart(productId) {
    setCart((prev) => prev.filter((line) => line.product.id !== productId))
  }

  function clearCart() {
    setCart([])
  }

  const cartTotal = cart.reduce((sum, line) => sum + line.product.price * line.quantity, 0)

  return (
    <CartContext.Provider value={{ cart, addToCart, setQuantity, removeFromCart, clearCart, cartTotal }}>
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  return useContext(CartContext)
}
