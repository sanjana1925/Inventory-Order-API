# Inventory & Order Management API

A FastAPI + SQLite B2B portal: business clients browse a catalog, request quotes,
place purchase orders, and track them; admins manage products, inventory,
suppliers, procurement, customers, and reporting. A Streamlit app on top
provides the actual client/admin UI.

## Schema

| table | key fields |
|---|---|
| `products` | `id`, `name`, `category`, `price`, `stock_qty` |
| `categories` | `id`, `name` — a suggested list; `products.category` is a denormalized string, not an FK to this table |
| `customers` | `id`, `name`, `email`, `phone`, `address`, `password_hash` (nullable — only signed-up accounts can log in) |
| `delivery_addresses` | `id`, `customer_id` -> customers, `label`, `address`, `is_default` |
| `orders` | `id`, `customer_name`, `customer_id` -> customers (nullable), `po_reference`, `created_at`, `status` |
| `order_items` | `id`, `order_id` -> orders, `product_id` -> products, `quantity`, `unit_price` |
| `quotes` / `quote_items` | a client's request for pricing before committing to an order; converts into a real `order` once priced and accepted |
| `suppliers` | `id`, `name`, `city`, `state` |
| `purchase_orders` / `purchase_order_items` | the admin side of procurement — buying stock from a supplier to replenish inventory |
| `support_messages` | `id`, `customer_name`, `customer_id`, `email`, `subject`, `message`, `status` |
| `notifications` | `id`, `audience` (`admin`/`client`), `message`, `level`, `order_id` |
| `users` | admin/staff accounts (separate from `customers`, which is the client side) |

`unit_price` on an order line is copied from the product at order time, not read
live off the product — past orders keep showing what was actually charged even
if the product's price changes later.

`orders.customer_name` is a free-text display field; `orders.customer_id` (added
after `Order`/`Quote`/`SupportMessage` all originally scoped "my records" by a
fuzzy name match, which let one customer see another's data if their names
overlapped) is the real identity boundary and should be used for any
per-customer filtering. It's nullable because an admin can place an order on
behalf of a company that hasn't signed up for an account yet.

## Order lifecycle

`pending -> processing -> shipped -> delivered`, or `pending`/`processing ->
cancelled`. Enforced server-side (`app/security.py::can_transition`) — e.g. you
can't skip straight from `pending` to `shipped`, and a `shipped` order can no
longer be cancelled. Cancelling returns each line's quantity to stock.

## Oversell prevention

`POST /orders` validates every line's stock *before* writing anything. If any
product in a multi-line order is missing or short, the whole order is rejected
with a `400` and no stock is touched. Quantities for duplicate product lines
within the same order are summed before the stock check.

## Quotes

`POST /quotes` requests pricing on a set of products (no stock check — it's
speculative). An admin prices it (`PATCH /quotes/{id}/price`), which moves it
to `quoted`. The client (or admin) then converts it (`POST
/quotes/{id}/convert`), which re-checks stock and creates a real `Order` at the
*negotiated* prices, not the live product price.

## Procurement

Separate from client-facing orders: `POST /purchase-orders` records buying
stock from a `supplier`; `POST /purchase-orders/{id}/receive` adds the ordered
quantities to `products.stock_qty` and marks it received (receiving twice is
rejected, not double-applied).

## Endpoints

- Products: `GET/POST /products`, `GET/PUT/DELETE /products/{id}`,
  `GET /products/categories`, `GET /products/low-stock`
- Categories: `GET/POST /categories`, `DELETE /categories/{id}`
- Customers: `GET/POST /customers`, `GET/PUT/DELETE /customers/{id}`,
  `POST /customers/signup`, `POST /customers/login`
- Delivery addresses: `GET/POST /customers/{id}/addresses`,
  `DELETE /customers/{id}/addresses/{address_id}`
- Orders: `GET/POST /orders`, `GET /orders/{id}`, `GET /orders/lookup`
  (public tracking by id + customer name), `PATCH /orders/{id}/status`,
  `POST /orders/{id}/cancel`, `GET /orders/{id}/invoice` (PDF)
- Quotes: `GET/POST /quotes`, `GET /quotes/{id}`, `PATCH /quotes/{id}/price`,
  `POST /quotes/{id}/reject`, `POST /quotes/{id}/convert`
- Suppliers: `GET/POST /suppliers`, `DELETE /suppliers/{id}`
- Purchase orders: `GET/POST /purchase-orders`, `GET /purchase-orders/{id}`,
  `POST /purchase-orders/{id}/receive`
- Support: `GET/POST /support`, `POST /support/{id}/close`
- Notifications: `GET /notifications?audience=admin|client`
- Users (admin/staff accounts): `GET/POST /users`, `DELETE /users/{id}`,
  `PATCH /users/{id}/password`, `POST /auth/login`
- Reports: `GET /reports/overview`, `/sales`, `/inventory`, `/low-stock`,
  `/top-products`, `/top-customers`, `/revenue-trend`, `/category-mix`

Most list endpoints accept `skip`/`limit` and return the total match count in
an `X-Total-Count` response header.

## Streamlit UI

`app/streamlit_app.py` is the only client/admin-facing UI — the API itself has
no auth-gated pages, just `/docs`. Both roles land on a Dashboard with a
sidebar nav (icons throughout, e.g. 🔔 for Notifications) built on top of the
endpoints above:

- **Client dashboard** — recent orders, a "Need help?" complaint form (posts
  to `/support`, with a call-support number alongside it), and a shortcut into
  the catalog/purchase-order flow.
- **Admin dashboard** — headline metrics, a low-stock panel that highlights
  critical items (red) vs warning items (orange) with an inline **Restock**
  button next to each (`PUT /products/{id}`), and a "Delivered — awaiting
  completion" list with a one-click **Mark completed** button
  (`PATCH /orders/{id}/status`) so admin doesn't have to hunt through the full
  Orders page just to close out delivered orders.

## Errors

- `422` — malformed input (bad types, negative price/qty). Handled by Pydantic.
- `400` — a business rule violated by well-typed input: insufficient stock, an
  invalid order-status transition, deleting a product still referenced by an
  order/quote/purchase-order, a duplicate email/code, etc.
- `404` — an id-based lookup where the id doesn't exist.

## Known limitations

This is a local demo, not a production deployment:

- **No server-side authorization.** Every endpoint is open — the client/admin
  split is enforced by the Streamlit UI only, not the API. `/customers/login`
  and `/auth/login` return the account on success but issue no session token;
  Streamlit just remembers it client-side. Anyone hitting the API directly
  (e.g. `/docs`) has full access.
- No rate limiting or lockout on the login endpoints.
- Plain HTTP, no TLS (fine for `localhost`).
- `products.category` is a denormalized string, not a foreign key to
  `categories` — deleting a category doesn't touch existing products, and a
  product's category can reference a name that isn't (or is no longer) in the
  `categories` table.

## Running

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Seed the database first (see "Seeding" below), then start both processes —
each in its own terminal:

```
uvicorn app.main:app --reload           # API on http://127.0.0.1:8000
streamlit run app/streamlit_app.py      # UI on  http://127.0.0.1:8501
```

The API must already be running before you open the Streamlit UI, since every
page in it calls out to `http://127.0.0.1:8000`. `/docs` gives you interactive
Swagger docs for the API directly. Log into the Streamlit UI as a business
client via "Sign up" on the login screen, or as admin/staff with whatever
account your seed script created (`scripts/seed_big_dataset.py` creates
`admin@inventory.com` / `admin123`; `scripts/seed.py` doesn't create any
login — add one via `POST /users`).

### Tests

```
pytest
```

## Seeding

Two options, both drop and recreate all tables first:

- `python scripts/seed.py` — a handful of hand-written demo products only, no
  customers/orders/suppliers. Fastest way to get the API into a runnable
  state; doesn't create a users login.
- `python scripts/seed_big_dataset.py` — a full synthetic dataset for
  exercising every screen in the UI: 576 customers, 57 suppliers, ~49
  products across 4 categories (Home Appliances, Furniture, Mobile
  Appliances, Home Decor), and 607 orders placed through the real API (so
  oversell prevention and stock decrement actually run) spread across
  pending/processing/shipped/delivered/completed/cancelled. Also creates the
  `admin@inventory.com` / `admin123` login. Takes a few seconds to run and
  prints a summary (revenue, low-stock count, order status breakdown) when done.
