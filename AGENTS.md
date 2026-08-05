# AGENTS.md

Guidance for AI coding agents working in this repo. See [README.md](README.md)
first for the schema, endpoints, and business rules (order lifecycle, oversell prevention,
quotes, procurement) — this file only covers things the README doesn't: how to run things
and the conventions to follow when changing code.

## Stack

FastAPI + SQLAlchemy 2.0 (`Mapped`/`mapped_column` style) + SQLite, Pydantic v2 schemas,
pytest, Streamlit for the UI. No auth/session layer — see "Known limitations" in the README
before adding anything that assumes one.

## Running

```
venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed_big_dataset.py     # or scripts/seed.py for a minimal seed
uvicorn app.main:app --reload          # API on :8000
streamlit run app/streamlit_app.py     # UI on :8501, needs the API running
pytest                                  # 37 tests, in-memory SQLite, no seed needed
```

## Layout

- `app/models.py` — SQLAlchemy models, one file, grouped by feature with a comment header
  per section.
- `app/schemas.py` — Pydantic request/response models, same grouping/order as `models.py`.
- `app/routers/<feature>.py` — one router per resource, each owns its own DB queries; no
  service/repository layer. Mirror this file-per-resource split for any new resource rather
  than growing an existing router or introducing a new layer.
- `app/security.py` — password hashing (PBKDF2) and the order-status transition table
  (`can_transition`). Not an auth/session module despite the name.
- `app/activity.py` — `notify()`, the one function that writes to `notifications`.
- `app/invoice.py` — PDF generation for `GET /orders/{id}/invoice` (fpdf2).
- `app/frontend_helpers.py` — pure functions shared by `streamlit_app.py` (formatting,
  small calculations) so they're unit-testable without spinning up Streamlit.
- `scripts/seed.py` / `scripts/seed_big_dataset.py` — both drop and recreate all tables.

## Conventions to match

- **Router pattern**: a private `_get_x_or_404` helper for id lookups; list endpoints take
  `skip`/`limit` (`Query(ge=..., le=...)`), set `response.headers["X-Total-Count"]` from a
  separate count query, and return `list[XOut]`. Follow this shape for new list/detail
  endpoints rather than inventing pagination differently per resource.
- **Errors**: `422` is Pydantic's (don't hand-roll type/range validation that Pydantic
  `Field` constraints already cover); `400` for business-rule violations, raised explicitly
  via `HTTPException`; `404` for missing ids. Keep using this split — don't return `400` for
  a missing id or `404` for a business-rule failure.
- **Serialization**: simple models return the ORM object directly (`response_model` handles
  it via `from_attributes=True`). Anything with a computed field (`OrderOut.total`,
  `PurchaseOrderOut.total_cost`, `OrderItemOut.line_total`) uses an explicit
  `_serialize_x()` function instead of a `@property` on the model — keep computed fields out
  of `models.py`.
- **Timestamps**: `datetime.now(timezone.utc).replace(tzinfo=None)` — stored naive-UTC by
  convention. Don't mix in `datetime.now()` (local time) or a tz-aware value; both will sort
  wrong against existing rows.
- **Multi-line requests** (orders, quotes, purchase orders): sum quantities per
  `product_id` before validating/applying stock, so two lines for the same product in one
  request don't bypass the stock check. Follow the pattern in
  [orders.py](app/routers/orders.py) (`requested_qty` dict) for any new multi-line endpoint.
- **Delete guards**: before deleting a row other tables reference by FK (see
  `_referenced_elsewhere` in [products.py](app/routers/products.py)), check for references
  and `400` rather than letting SQLite raise or cascading silently.
- **Identity**: use `customer_id` for anything access-control-shaped (a client's own
  orders/quotes/support tickets); `customer_name` is a free-text display field only. This
  distinction exists because of a real bug — see the README schema section.

## Tests

`tests/conftest.py` gives every test a fresh in-memory SQLite DB via `client`/`make_product`
fixtures — no test should touch `inventory.db` or depend on seed data. Add new fixtures
there rather than duplicating setup per test file. Run the whole suite (`pytest`, no `-k`)
before considering a change done — it's fast (~2s).

## Known gaps (see README for full list)

No server-side auth — every endpoint is open regardless of role. Don't add UI-only access
checks to `streamlit_app.py` and consider that "secured"; if a change needs real
authorization, it has to happen in the API layer, which doesn't exist yet.
