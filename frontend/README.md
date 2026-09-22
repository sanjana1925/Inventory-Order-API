# Frontend (React + Tailwind)

A small React SPA covering the core buy/sell/fulfill loop against the existing
FastAPI backend. Plain JSX, no TypeScript; hooks + context only, no state
library; `react-router-dom` for routing.

## Prerequisites

- Node.js (v18+)
- The FastAPI backend already running on `http://127.0.0.1:8000` (see the
  root `README.md` — `uvicorn app.main:app --reload`, after seeding the DB)

## Run

```
npm install
npm run dev
```

Opens on `http://localhost:5173`. API calls are proxied through Vite's dev
server to `http://127.0.0.1:8000` (see `vite.config.js`) — this is required
because the backend has no CORS middleware, so a direct cross-origin fetch
from the browser would otherwise be blocked.

## Pages

1. **Login/Signup** (`/login`) — business client signup/login, or admin/staff
   login (staff accounts are bootstrapped via `POST /users`, not from this UI)
2. **Catalog** (`/catalog`) — browse/search products, add to cart, place order
3. **My Orders** (`/my-orders`) — pay (simulated), cancel, download invoice
4. **Admin Dashboard** (`/admin`) — stats from `GET /reports/overview`
5. **Products** (`/admin/products`) — create, inline edit, delete
6. **Orders** (`/admin/orders`) — advance order status

Build with `npm run build`; output goes to `dist/`.
