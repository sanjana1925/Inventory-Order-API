import AdminSidebar from './AdminSidebar'

export default function AdminLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-yellow-50">
      <AdminSidebar />
      <main className="min-w-0 flex-1 px-9 py-8">{children}</main>
    </div>
  )
}
