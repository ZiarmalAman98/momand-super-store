import { Link } from 'react-router-dom'
import { MapPin, Phone, Store } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-container footer-grid">
        <div className="footer-brand"><div className="footer-logo"><Store size={23} /><strong>Momand Super Store</strong></div><p>Your trusted store for quality products and everyday essentials.</p></div>
        <div><h3>Explore</h3><Link to="/shop">Shop all products</Link><Link to="/categories">Categories</Link><Link to="/about">About us</Link></div>
        <div><h3>Customer care</h3><Link to="/contact">Contact us</Link><Link to="/account">My orders</Link><Link to="/cart">Shopping cart</Link></div>
        <div><h3>Store information</h3><p><MapPin size={15} /> Store address to be configured</p><p><Phone size={15} /> Store phone to be configured</p></div>
      </div>
      <div className="site-container footer-bottom">© {new Date().getFullYear()} Momand Super Store. All rights reserved.</div>
    </footer>
  )
}
