// Shared Tailwind class strings for the admin design system, so the sidebar
// layout, cards, tables, inputs, and buttons look consistent across every
// /admin/* page instead of each file inventing its own variant.

export const ADMIN_INPUT =
  'border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-yellow-400/50 focus:border-yellow-400'

export const ADMIN_BUTTON_PRIMARY =
  'bg-yellow-400 hover:bg-yellow-500 disabled:opacity-50 text-slate-900 rounded-lg px-3.5 py-1.5 text-sm font-semibold'

export const ADMIN_BUTTON_SECONDARY =
  'border border-slate-300 rounded-lg px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100'

export const ADMIN_TABLE_WRAP =
  'overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_1px_3px_rgba(15,23,42,0.04),0_4px_16px_rgba(15,23,42,0.06)]'

export const ADMIN_THEAD_TR = 'border-b border-slate-200 bg-slate-100 text-left'

export const ADMIN_TH = 'px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500'

export const ADMIN_TBODY_TR = 'border-b border-slate-100 last:border-b-0 hover:bg-slate-100'

export const ADMIN_TD = 'px-4 py-2.5 text-slate-700'
