import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Menu, Search, ShoppingBasket, Store, X } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [cartCount, setCartCount] = useState(0)
  const [query, setQuery] = useState('')
  const { user, logout } = useAuth()

  useEffect(() => {
    const refresh = () => api.cart().then((cart) => setCartCount(cart.count)).catch(() => {})
    refresh()
    window.addEventListener('cart-updated', refresh)
    return () => window.removeEventListener('cart-updated', refresh)
  }, [])

  const navClass = ({ isActive }) => `nav-link${isActive ? ' active' : ''}`
  return (
    <header className="site-header">
      <div className="announcement"><div className="site-container">Your neighborhood store, now online <span>•</span> Quality for every day</div></div>
      <div className="site-container header-main">
        <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={21} /> : <Menu size={21} />}
        </button>
        <Link className="brand" to="/" aria-label="Momand Super Store home">
          <span className="brand-mark"><Store size={23} /></span>
          <span><strong>Momand</strong><small>SUPER STORE</small></span>
        </Link>
        <form className="search-bar" onSubmit={(event) => { event.preventDefault(); window.location.href = `/shop${query ? `?search=${encodeURIComponent(query)}` : ''}` }}>
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search groceries and more" aria-label="Search products" />
          <button type="submit">Search</button>
        </form>
        <div className="header-actions">
          <Link className="account-action" to={user ? '/account' : '/login'}><span>{user ? `Hi, ${user.first_name || user.email.split('@')[0]}` : 'Account'}</span><small>{user ? 'My account' : 'Login / Register'}</small></Link>
          <Link className="cart-action" to="/cart" aria-label={`Cart, ${cartCount} items`}><ShoppingBasket size={22} /><span className="cart-count">{cartCount}</span><small>Cart</small></Link>
        </div>
      </div>
      <nav className={`main-nav${menuOpen ? ' open' : ''}`}>
        <div className="site-container nav-content">
          <NavLink to="/shop" className={navClass} onClick={() => setMenuOpen(false)}>Shop</NavLink>
          <NavLink to="/categories" className={navClass} onClick={() => setMenuOpen(false)}>Categories</NavLink>
          <NavLink to="/about" className={navClass} onClick={() => setMenuOpen(false)}>About us</NavLink>
          <NavLink to="/contact" className={navClass} onClick={() => setMenuOpen(false)}>Contact</NavLink>
          {user?.is_staff && <NavLink to="/dashboard" className={navClass} onClick={() => setMenuOpen(false)}>Dashboard</NavLink>}
          {user?.is_staff && <NavLink to="/pos" className={navClass} onClick={() => setMenuOpen(false)}>POS</NavLink>}
          {user && <NavLink to="/account" className={navClass} onClick={() => setMenuOpen(false)}>Orders</NavLink>}
          {user && <button className="nav-link nav-button" onClick={logout}>Sign out</button>}
        </div>
      </nav>
    </header>
  )
}
