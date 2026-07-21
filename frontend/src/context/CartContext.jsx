import { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'

const CartCtx = createContext(null)
const STORAGE_KEY = 'cart_items'

function readStored() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return Array.isArray(raw) ? raw : []
  } catch {
    return []
  }
}

export function CartProvider({ children }) {
  const { user, loading } = useAuth()
  const [items, setItems] = useState(readStored)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, [items])

  // Don't leak one student's cart into the next login on a shared device — but
  // `user` is null for a moment on every page load while auth is still resolving
  // (loading === true), not just on an actual logout. Only clear once auth has
  // actually finished checking and genuinely found no user.
  useEffect(() => {
    if (!loading && !user) setItems([])
  }, [user, loading])

  const addItem = (course) => {
    setItems(prev => prev.some(i => i.id === course.id) ? prev : [...prev, course])
  }
  const removeItem = (id) => setItems(prev => prev.filter(i => i.id !== id))
  const clear = () => setItems([])
  const has = (id) => items.some(i => i.id === id)

  return (
    <CartCtx.Provider value={{ items, addItem, removeItem, clear, has }}>
      {children}
    </CartCtx.Provider>
  )
}

export const useCart = () => useContext(CartCtx)
