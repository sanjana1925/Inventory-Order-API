export default function Card({ title, children, className = '' }) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white p-4 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_4px_16px_rgba(15,23,42,0.06)] ${className}`}
    >
      {title && <h2 className="mb-3 text-[15px] font-semibold text-slate-900">{title}</h2>}
      {children}
    </div>
  )
}
