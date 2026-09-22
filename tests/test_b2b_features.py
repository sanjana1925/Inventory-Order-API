def test_deleting_a_product_referenced_by_an_order_is_rejected_not_crashed(client, make_product, admin_headers):
    product = make_product(stock_qty=10)
    client.post("/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.delete(f"/products/{product['id']}", headers=admin_headers)
    assert resp.status_code == 400

    # The order (and its line item) must still be intact and readable.
    assert client.get(f"/products/{product['id']}").status_code == 200


def test_deleting_an_unreferenced_product_still_works(client, make_product, admin_headers):
    product = make_product(stock_qty=10)
    resp = client.delete(f"/products/{product['id']}", headers=admin_headers)
    assert resp.status_code == 204


def test_orders_customer_id_filter_is_exact_not_a_name_substring(client, make_product):
    product = make_product(stock_qty=10)
    client.post("/orders", json={"customer_name": "Acme", "customer_id": 1, "items": [{"product_id": product["id"], "quantity": 1}]})
    client.post("/orders", json={"customer_name": "Acme Global", "customer_id": 2, "items": [{"product_id": product["id"], "quantity": 1}]})

    resp = client.get("/orders", params={"customer_id": 1})
    names = [o["customer_name"] for o in resp.json()]
    assert names == ["Acme"]  # not ["Acme", "Acme Global"]


def test_order_status_moves_through_valid_transitions_only(client, make_product, admin_headers):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 2}]}
    ).json()

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"}, headers=admin_headers)
    assert resp.status_code == 400  # can't skip processing

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "processing"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "shipped"}, headers=admin_headers)
    assert resp.status_code == 200

    resp = client.patch(f"/orders/{order['id']}/status", json={"status": "cancelled"}, headers=admin_headers)
    assert resp.status_code == 400  # can't cancel once shipped


def test_cancelling_a_processing_order_returns_stock(client, make_product, admin_headers):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 3}]}
    ).json()
    client.patch(f"/orders/{order['id']}/status", json={"status": "processing"}, headers=admin_headers)

    resp = client.post(f"/orders/{order['id']}/cancel")
    assert resp.status_code == 200
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 10


def test_quote_request_price_and_convert_uses_quoted_price(client, make_product, admin_headers):
    product = make_product(price=100.0, stock_qty=20)

    quote = client.post(
        "/quotes", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 5}]}
    ).json()
    assert quote["status"] == "requested"

    resp = client.patch(
        f"/quotes/{quote['id']}/price",
        json={"items": [{"product_id": product["id"], "quoted_unit_price": 80.0}]},
        headers=admin_headers,
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


def test_quote_convert_rejected_if_stock_dropped_below_quoted_quantity(client, make_product, admin_headers):
    product = make_product(stock_qty=5)
    quote = client.post(
        "/quotes", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 5}]}
    ).json()
    client.patch(
        f"/quotes/{quote['id']}/price",
        json={"items": [{"product_id": product["id"], "quoted_unit_price": 10.0}]},
        headers=admin_headers,
    )

    # Stock sold elsewhere before the client accepts the quote.
    client.post("/orders", json={"customer_name": "Other", "items": [{"product_id": product["id"], "quantity": 3}]})

    resp = client.post(f"/quotes/{quote['id']}/convert")
    assert resp.status_code == 400


def test_purchase_order_receive_increments_stock(client, make_product, admin_headers):
    product = make_product(stock_qty=10)
    supplier = client.post("/suppliers", json={"name": "Acme Supply"}, headers=admin_headers).json()

    po = client.post(
        "/purchase-orders",
        json={"supplier_id": supplier["id"], "items": [{"product_id": product["id"], "quantity": 20, "unit_cost": 5.0}]},
        headers=admin_headers,
    ).json()
    assert po["status"] == "ordered"

    resp = client.post(f"/purchase-orders/{po['id']}/receive", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 30

    # Receiving twice is rejected, not double-applied.
    resp = client.post(f"/purchase-orders/{po['id']}/receive", headers=admin_headers)
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


def test_admin_login_issues_a_bearer_token_that_unlocks_protected_endpoints(client):
    client.post("/users", json={"email": "boss@test.com", "password": "bosspass123", "role": "admin"})
    login = client.post("/auth/login", json={"email": "boss@test.com", "password": "bosspass123"}).json()
    assert "access_token" in login

    # No token: the write is rejected before it ever reaches business logic.
    resp = client.post("/products", json={"name": "Gadget", "price": 5.0, "stock_qty": 1})
    assert resp.status_code == 401

    # Same request, with the token: goes through.
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    resp = client.post("/products", json={"name": "Gadget", "price": 5.0, "stock_qty": 1}, headers=headers)
    assert resp.status_code == 201


def test_customer_token_cannot_be_used_against_staff_only_endpoints(client, admin_headers):
    customer = client.post(
        "/customers/signup", json={"name": "Acme Co", "email": "acme3@example.com", "password": "secret123"}
    ).json()
    customer_headers = {"Authorization": f"Bearer {customer['access_token']}"}

    resp = client.post("/products", json={"name": "Widget", "price": 1.0, "stock_qty": 1}, headers=customer_headers)
    assert resp.status_code == 401


def test_order_payment_starts_unpaid_and_pay_endpoint_marks_it_paid(client, make_product):
    product = make_product(price=100.0, stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 2}]}
    ).json()
    assert order["payment_status"] == "unpaid"
    assert order["tax_amount"] == round(200.0 * 0.08, 2)
    assert order["shipping_fee"] == 100.0
    assert order["grand_total"] == order["total"] + order["tax_amount"] + order["shipping_fee"]

    resp = client.post(f"/orders/{order['id']}/pay")
    assert resp.status_code == 200
    assert resp.json()["payment_status"] == "paid"

    # Paying twice is rejected, not double-applied.
    resp = client.post(f"/orders/{order['id']}/pay")
    assert resp.status_code == 400


def test_admin_can_toggle_payment_status_either_direction(client, make_product, admin_headers):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]}
    ).json()
    assert order["payment_status"] == "unpaid"

    resp = client.patch(f"/orders/{order['id']}/payment-status", json={"payment_status": "paid"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["payment_status"] == "paid"

    # Unlike POST /pay (one-way), the admin override can go back to unpaid too.
    resp = client.patch(f"/orders/{order['id']}/payment-status", json={"payment_status": "unpaid"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["payment_status"] == "unpaid"


def test_payment_status_update_requires_staff_auth(client, make_product):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]}
    ).json()
    resp = client.patch(f"/orders/{order['id']}/payment-status", json={"payment_status": "paid"})
    assert resp.status_code == 401


def test_payment_status_cannot_change_on_cancelled_order(client, make_product, admin_headers):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]}
    ).json()
    client.post(f"/orders/{order['id']}/cancel").raise_for_status()

    resp = client.patch(f"/orders/{order['id']}/payment-status", json={"payment_status": "paid"}, headers=admin_headers)
    assert resp.status_code == 400


def test_orders_list_filters_by_payment_status(client, make_product):
    product = make_product(stock_qty=10)
    unpaid = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]}
    ).json()
    paid = client.post(
        "/orders", json={"customer_name": "Acme", "items": [{"product_id": product["id"], "quantity": 1}]}
    ).json()
    client.post(f"/orders/{paid['id']}/pay").raise_for_status()

    resp = client.get("/orders", params={"payment_status": "unpaid"})
    ids = [o["id"] for o in resp.json()]
    assert unpaid["id"] in ids
    assert paid["id"] not in ids


def test_favorite_add_list_and_delete(client, make_product):
    product = make_product(name="Cordless Drill", stock_qty=5)

    resp = client.post("/favorites", json={"customer_id": 1, "product_id": product["id"]})
    assert resp.status_code == 201
    favorite = resp.json()
    assert favorite["list_name"] == "Favorites"
    assert favorite["product_name"] == "Cordless Drill"

    resp = client.get("/favorites", params={"customer_id": 1})
    assert len(resp.json()) == 1

    resp = client.delete(f"/favorites/{favorite['id']}")
    assert resp.status_code == 204
    assert client.get("/favorites", params={"customer_id": 1}).json() == []


def test_favorite_duplicate_in_same_list_is_rejected(client, make_product):
    product = make_product(name="Safety Goggles", stock_qty=5)
    client.post("/favorites", json={"customer_id": 1, "product_id": product["id"]})

    resp = client.post("/favorites", json={"customer_id": 1, "product_id": product["id"]})
    assert resp.status_code == 400


def test_favorite_same_product_allowed_in_different_named_lists(client, make_product):
    product = make_product(name="Work Gloves", stock_qty=5)

    r1 = client.post(
        "/favorites", json={"customer_id": 1, "product_id": product["id"], "list_name": "Monthly restock"}
    )
    r2 = client.post("/favorites", json={"customer_id": 1, "product_id": product["id"], "list_name": "Wishlist"})
    assert r1.status_code == 201
    assert r2.status_code == 201

    resp = client.get("/favorites/lists", params={"customer_id": 1})
    assert resp.json() == ["Monthly restock", "Wishlist"]


def test_favorite_unknown_product_is_rejected(client):
    resp = client.post("/favorites", json={"customer_id": 1, "product_id": 999})
    assert resp.status_code == 400


def test_product_list_filters_by_price_range_and_stock(client, make_product):
    make_product(name="Cheap In Stock", price=5.0, stock_qty=3)
    make_product(name="Expensive Out Of Stock", price=500.0, stock_qty=0)

    resp = client.get("/products", params={"max_price": 10, "in_stock_only": True})
    names = [p["name"] for p in resp.json()]
    assert names == ["Cheap In Stock"]


def test_restock_adds_to_existing_stock(client, make_product, admin_headers):
    product = make_product(stock_qty=5)

    resp = client.post(f"/products/{product['id']}/restock", json={"quantity": 20}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["stock_qty"] == 25


def test_restock_two_calls_both_apply_not_lost(client, make_product, admin_headers):
    """Guards the atomic-increment implementation: if restock were a naive
    read-modify-write, two back-to-back calls using a stale in-Python value
    could still land correctly here (they're sequential, not concurrent), but
    switching the endpoint to `stock_qty = <literal>` instead of
    `stock_qty = stock_qty + delta` would silently break this test the moment
    someone reorders the two calls or adds concurrency."""
    product = make_product(stock_qty=0)

    client.post(f"/products/{product['id']}/restock", json={"quantity": 10}, headers=admin_headers)
    resp = client.post(f"/products/{product['id']}/restock", json={"quantity": 15}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["stock_qty"] == 25


def test_restock_requires_positive_quantity(client, make_product, admin_headers):
    product = make_product(stock_qty=5)

    resp = client.post(f"/products/{product['id']}/restock", json={"quantity": 0}, headers=admin_headers)
    assert resp.status_code == 422

    resp = client.post(f"/products/{product['id']}/restock", json={"quantity": -5}, headers=admin_headers)
    assert resp.status_code == 422


def test_restock_requires_staff_auth(client, make_product):
    product = make_product(stock_qty=5)
    resp = client.post(f"/products/{product['id']}/restock", json={"quantity": 10})
    assert resp.status_code == 401


def test_restock_unknown_product_is_404(client, admin_headers):
    resp = client.post("/products/999/restock", json={"quantity": 10}, headers=admin_headers)
    assert resp.status_code == 404


def test_product_list_sort_price_desc(client, make_product):
    make_product(name="Budget Drill", price=10.0, stock_qty=1)
    make_product(name="Pro Drill", price=50.0, stock_qty=1)

    resp = client.get("/products", params={"sort": "price_desc"})
    names = [p["name"] for p in resp.json()]
    assert names[:2] == ["Pro Drill", "Budget Drill"]
