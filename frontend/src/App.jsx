import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Navbar from './components/Navbar'
import AdminLayout from './components/AdminLayout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import CatalogPage from './pages/CatalogPage'
import QuickOrderPage from './pages/QuickOrderPage'
import FavoritesPage from './pages/FavoritesPage'
import MyOrdersPage from './pages/MyOrdersPage'
import AdminDashboardPage from './pages/AdminDashboardPage'
import AdminProductsPage from './pages/AdminProductsPage'
import AdminOrdersPage from './pages/AdminOrdersPage'
import AdminCustomersPage from './pages/AdminCustomersPage'
import AdminCategoriesPage from './pages/AdminCategoriesPage'
import AdminSuppliersPage from './pages/AdminSuppliersPage'
import AdminPurchaseOrdersPage from './pages/AdminPurchaseOrdersPage'
import AdminUsersPage from './pages/AdminUsersPage'
import AdminReportsPage from './pages/AdminReportsPage'
import QuotesPage from './pages/QuotesPage'
import SupportPage from './pages/SupportPage'
import NotificationsPage from './pages/NotificationsPage'
import AddressesPage from './pages/AddressesPage'
import ProfilePage from './pages/ProfilePage'

// Admin/staff routes get the sidebar layout instead of the top navbar.
function AdminRoute({ children }) {
  return (
    <ProtectedRoute role="staff">
      <AdminLayout>{children}</AdminLayout>
    </ProtectedRoute>
  )
}

export default function App() {
  const path = useLocation().pathname
  const isAdmin = path.startsWith('/admin')
  // The login page is its own full-bleed branded layout — no top navbar or
  // centered/padded wrapper on top of it, same reasoning as the admin sidebar.
  const isBare = isAdmin || path === '/login'

  return (
    <div className="min-h-screen bg-yellow-50">
      {!isBare && <Navbar />}
      <main className={isBare ? '' : 'max-w-5xl mx-auto p-4'}>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/catalog"
            element={
              <ProtectedRoute role="customer">
                <CatalogPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/quick-order"
            element={
              <ProtectedRoute role="customer">
                <QuickOrderPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/favorites"
            element={
              <ProtectedRoute role="customer">
                <FavoritesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-orders"
            element={
              <ProtectedRoute role="customer">
                <MyOrdersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/quotes"
            element={
              <ProtectedRoute role="customer">
                <QuotesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/support"
            element={
              <ProtectedRoute role="customer">
                <SupportPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <ProtectedRoute role="customer">
                <NotificationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/addresses"
            element={
              <ProtectedRoute role="customer">
                <AddressesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute role="customer">
                <ProfilePage />
              </ProtectedRoute>
            }
          />

          <Route path="/admin" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
          <Route path="/admin/products" element={<AdminRoute><AdminProductsPage /></AdminRoute>} />
          <Route path="/admin/orders" element={<AdminRoute><AdminOrdersPage /></AdminRoute>} />
          <Route path="/admin/customers" element={<AdminRoute><AdminCustomersPage /></AdminRoute>} />
          <Route path="/admin/categories" element={<AdminRoute><AdminCategoriesPage /></AdminRoute>} />
          <Route path="/admin/suppliers" element={<AdminRoute><AdminSuppliersPage /></AdminRoute>} />
          <Route path="/admin/purchase-orders" element={<AdminRoute><AdminPurchaseOrdersPage /></AdminRoute>} />
          <Route path="/admin/quotes" element={<AdminRoute><QuotesPage /></AdminRoute>} />
          <Route path="/admin/support" element={<AdminRoute><SupportPage /></AdminRoute>} />
          <Route path="/admin/notifications" element={<AdminRoute><NotificationsPage /></AdminRoute>} />
          <Route path="/admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
          <Route path="/admin/reports" element={<AdminRoute><AdminReportsPage /></AdminRoute>} />
        </Routes>
      </main>
    </div>
  )
}
