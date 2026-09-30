import { Navigate, Route, Routes } from 'react-router-dom'
import StoreLayout from './layouts/StoreLayout'
import AdminLayout from './layouts/AdminLayout'
import AdminLoginPage from './pages/AdminLoginPage'
import AboutPage from './pages/AboutPage'
import AccountPage from './pages/AccountPage'
import CartPage from './pages/CartPage'
import CheckoutPage from './pages/CheckoutPage'
import CategoriesPage from './pages/CategoriesPage'
import ContactPage from './pages/ContactPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import OrdersPage from './pages/OrdersPage'
import ProductPage from './pages/ProductPage'
import POSPage from './pages/POSPage'
import POSSalesPage from './pages/POSSalesPage'
import POSReceiptPage from './pages/POSReceiptPage'
import DashboardPage from './pages/DashboardPage'
import InventoryPage from './pages/InventoryPage'
import SuppliersPage from './pages/SuppliersPage'
import PurchasesPage from './pages/PurchasesPage'
import ExpensesPage from './pages/ExpensesPage'
import POSReturnsPage from './pages/POSReturnsPage'
import RegisterPage from './pages/RegisterPage'
import ReceiptPage from './pages/ReceiptPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import ShopPage from './pages/ShopPage'

function NotFound() {
  return <section className="site-container page-section"><div className="state-card"><strong>We couldn’t find that page.</strong><p>The link may have changed or the page may not exist.</p><a className="text-link" href="/">Return to the store</a></div></section>
}

export default function App() {
  return <Routes>
    <Route element={<StoreLayout />}>
      <Route index element={<HomePage />} />
      <Route path="shop" element={<ShopPage />} />
      <Route path="categories" element={<CategoriesPage />} />
      <Route path="product/:slug" element={<ProductPage />} />
      <Route path="cart" element={<CartPage />} />
      <Route path="checkout" element={<CheckoutPage />} />
      <Route path="pos" element={<POSPage />} />
      <Route path="pos/sales" element={<POSSalesPage />} />
      <Route path="pos/returns" element={<POSReturnsPage />} />
      <Route path="pos/sales/:invoice" element={<POSReceiptPage />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="inventory" element={<InventoryPage />} />
      <Route path="suppliers" element={<SuppliersPage />} />
      <Route path="purchases" element={<PurchasesPage />} />
      <Route path="expenses" element={<ExpensesPage />} />
      <Route path="about" element={<AboutPage />} />
      <Route path="contact" element={<ContactPage />} />
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route path="forgot-password" element={<ForgotPasswordPage />} />
      <Route path="reset-password" element={<ResetPasswordPage />} />
      <Route path="account" element={<AccountPage />} />
      <Route path="orders" element={<OrdersPage />} />
      <Route path="orders/:number/receipt" element={<ReceiptPage />} />
      <Route path="welcome" element={<Navigate to="/" replace />} />
    </Route>

    <Route path="/admin/login" element={<AdminLoginPage />} />
    <Route path="/admin" element={<AdminLayout />}>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="pos" element={<POSPage />} />
      <Route path="pos/sales" element={<POSSalesPage />} />
      <Route path="pos/returns" element={<POSReturnsPage />} />
      <Route path="pos/sales/:invoice" element={<POSReceiptPage />} />
      <Route path="inventory" element={<InventoryPage />} />
      <Route path="purchases" element={<PurchasesPage />} />
      <Route path="suppliers" element={<SuppliersPage />} />
      <Route path="expenses" element={<ExpensesPage />} />
      <Route path="sales" element={<POSSalesPage />} />
      <Route path="reports" element={<DashboardPage />} />
      <Route path="customers" element={<AccountPage />} />
      <Route path="payments" element={<DashboardPage />} />
    </Route>

    <Route path="*" element={<NotFound />} />
  </Routes>
}
