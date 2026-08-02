# Inventory & Order Management API

A small FastAPI + SQLite service for tracking products and the orders placed against them.
Placing an order writes to two tables (`orders`, `order_items`) and decrements a third value
(`products.stock_qty`) in one operation — the part worth studying is how that stays atomic.

## Schema

| table | key fields |
|---|---|
| `products` | `id`, `name`, `price`, `stock_qty` |
| `orders` | `id`, `customer_name`, `created_at`, `status` |
| `order_items` | `id`, `order_id` -> orders, `product_id` -> products, `quantity`, `unit_price` |

`unit_price` is copied onto the order line at order time, not read live off the product. If a
product's price changes later, past orders still show what was actually charged.

## Oversell prevention

`POST /orders` validates every line's stock *before* writing anything. If any product in a
multi-line order is missing or short, the whole order is rejected with a `400` and no stock is
touched — a two-line order never half-succeeds. Quantities for duplicate product lines within
the same order are summed before the stock check, so two 3-unit lines against 5 units of stock
correctly fail as a combined request for 6.

## Endpoints

- `POST /products`, `GET /products`, `GET /products/{id}`, `PUT /products/{id}`,
  `DELETE /products/{id}`
- `GET /products/low-stock?threshold=10`
- `POST /orders` — `{customer_name, items: [{product_id, quantity}, ...]}`
- `GET /orders`, `GET /orders/{id}` (includes line items and computed total)
- `POST /orders/{id}/cancel` — returns stock to every product on the order

## Errors

- `422` — malformed input (bad types, negative price/qty). Handled by Pydantic.
- `400` — a business rule violated by well-typed input: insufficient stock, an unknown
  `product_id` inside an order, cancelling an already-cancelled order.
- `404` — a `/products/{id}` or `/orders/{id}` lookup where the id doesn't exist.

## Running / testing

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed.py
uvicorn app.main:app --reload
pytest
```
