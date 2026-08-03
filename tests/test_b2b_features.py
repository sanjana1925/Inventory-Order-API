def test_deleting_a_product_referenced_by_an_order_is_rejected_not_crashed(client, make_product):
    product = make_product(stock_qty=10)
    client.post("/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.delete(f"/products/{product['id']}")
    assert resp.status_code == 400

    # The order (and its line item) must still be intact and readable.
    assert client.get(f"/products/{product['id']}").status_code == 200


def test_deleting_an_unreferenced_product_still_works(client, make_product):
    product = make_product(stock_qty=10)
    resp = client.delete(f"/products/{product['id']}")
    assert resp.status_code == 204


def test_orders_customer_id_filter_is_exact_not_a_name_substring(client, make_product):
    product = make_product(stock_qty=10)
    client.post("/orders", json={"customer_name": "Acme", "customer_id": 1, "items": [{"product_id": product["id"], "quantity": 1}]})
    client.post("/orders", json={"customer_name": "Acme Global", "customer_id": 2, "items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.get("/orders", params={"customer_id": 1})
    names = [o["customer_name"] for o in resp.json()]
    assert names == ["Acme"]  # not ["Acme", "Acme Global"]


def test_order_status_moves_through_valid_transitions_only(client, make_product):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 2}]}
    ).json()

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"})
    assert resp.status_code == 400  # can't skip processing

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "processing"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"})
    assert resp.status_code == 200

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "cancelled"})
    assert resp.status_code == 400  # can't cancel once shipped


def test_cancelling_a_processing_order_returns_stock(client, make_product):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 3}]}
    ).json()
    client.patch(f"/orders/{order['id']}/status", json={"status": "processing"})

    resp = client.post(f"/orders/{order['id']}/cancel")
    assert resp.status_code == 200
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 10


def test_quote_request_price_and_convert_uses_quoted_price(client, make_product):
    product = make_product(price=100.0, stock_qty=20)

    quote = client.post(
        "/quotes", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 5}]}
    ).json()
    assert quote["status"] == "requested"

    resp = client.patch(
        f"/quotes/{quote['id']}/price",
        json={"items": [{"product_id": product["id"], "quoted_unit_price": 80.0}]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "quoted"

    resp = client.post(f"/quotes/{quote['id']}/convert")
    assert resp.status_code == 200
    assert resp.json()["status"] == "converted"
    order_id = resp.json()["order_id"]

    order = client.get(f"/orders/{order_id}").json()
    assert order["items"][0]["unit_price"] == 80.0  # negotiated price, not the live product price
    assert order["total"] == 400.0
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 15


def test_quote_cannot_convert_before_pricing(client, make_product):
    product = make_product(stock_qty=10)
    quote = client.post(
        "/quotes", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]}
    ).json()

    resp = client.post(f"/quotes/{quote['id']}/convert")
    assert resp.status_code == 400


def test_quote_convert_rejected_if_stock_dropped_below_quoted_quantity(client, make_product):
    product = make_product(stock_qty=5)
    quote = client.post(
        "/quotes", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 5}]}
    ).json()
    client.patch(f"/quotes/{quote['id']}/price", json={"items": [{"product_id": product["id"], "quoted_unit_price": 10.0}]})

    # Stock sold elsewhere before the client accepts the quote.
    client.post("/orders", json={"customer_name": "Other", "items": [{"product_id": product["id"], "quantity": 3}]})

    resp = client.post(f"/quotes/{quote['id']}/convert")
    assert resp.status_code == 400


def test_purchase_order_receive_increments_stock(client, make_product):
    product = make_product(stock_qty=10)
    supplier = client.post("/suppliers", json={"name": "Acme Supply"}).json()

    po = client.post(
        "/purchase-orders",
        json={"supplier_id": supplier["id"], "items": [{"product_id": product["id"], "quantity": 20, "unit_cost": 5.0}]},
    ).json()
    assert po["status"] == "ordered"

    resp = client.post(f"/purchase-orders/{po['id']}/receive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 30

    # Receiving twice is rejected, not double-applied.
    resp = client.post(f"/purchase-orders/{po['id']}/receive")
    assert resp.status_code == 400
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 30


def test_customer_signup_login_and_wrong_password(client):
    resp = client.post(
        "/customers/signup",
        json={"name": "Acme Co", "email": "acme@example.com", "password": "secret123"},
    )
    assert resp.status_code == 201

    resp = client.post("/customers/login", json={"email": "acme@example.com", "password": "secret123"})
    assert resp.status_code == 200

    resp = client.post("/customers/login", json={"email": "acme@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_delivery_address_marked_default_unsets_previous_default(client):
    customer = client.post(
        "/customers/signup", json={"name": "Acme Co", "email": "acme2@example.com", "password": "secret123"}
    ).json()

    client.post(f"/customers/{customer['id']}/addresses", json={"label": "HQ", "address": "1 Main St", "is_default": True})
    client.post(f"/customers/{customer['id']}/addresses", json={"label": "Warehouse", "address": "2 Side St", "is_default": True})

    addresses = client.get(f"/customers/{customer['id']}/addresses").json()
    defaults = [a for a in addresses if a["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["label"] == "Warehouse"


def test_support_message_lifecycle(client):
    resp = client.post(
        "/support",
        json={"customer_name": "Acme", "email": "acme@example.com", "subject": "Help", "message": "Need help"},
    )
    assert resp.status_code == 201
    message_id = resp.json()["id"]
    assert resp.json()["status"] == "open"

    resp = client.post(f"/support/{message_id}/close")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


def test_admin_login_rejects_unknown_user(client):
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert resp.status_code == 401
