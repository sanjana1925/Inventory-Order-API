def test_place_order_decrements_stock_for_every_line(client, make_product):
    mouse = make_product(name="Mouse", stock_qty=10)
    keyboard = make_product(name="Keyboard", stock_qty=10)

    resp = client.post(
        "/orders",
        json={
            "customer_name": "Alice",
            "items": [
                {"product_id": mouse["id"], "quantity": 3},
                {"product_id": keyboard["id"], "quantity": 2},
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["total"] == 3 * mouse["price"] + 2 * keyboard["price"]

    assert client.get(f"/products/{mouse['id']}").json()["stock_qty"] == 7
    assert client.get(f"/products/{keyboard['id']}").json()["stock_qty"] == 8


def test_second_line_short_on_stock_rejects_whole_order_and_writes_nothing(client, make_product):
    """The hard part: a two-line order can't half-succeed.

    If line 1 has enough stock but line 2 doesn't, neither line should be
    written and product 1's stock must be untouched.
    """
    plenty = make_product(name="Plenty", stock_qty=100)
    scarce = make_product(name="Scarce", stock_qty=1)

    resp = client.post(
        "/orders",
        json={
            "customer_name": "Bob",
            "items": [
                {"product_id": plenty["id"], "quantity": 5},
                {"product_id": scarce["id"], "quantity": 5},
            ],
        },
    )
    assert resp.status_code == 400
    problems = resp.json()["detail"]["problems"]
    assert any(p["product_id"] == scarce["id"] for p in problems)

    # Line 1 must not have been decremented even though it alone was valid.
    assert client.get(f"/products/{plenty['id']}").json()["stock_qty"] == 100
    assert client.get(f"/products/{scarce['id']}").json()["stock_qty"] == 1
    assert client.get("/orders").json() == []


def test_duplicate_product_lines_are_aggregated_before_stock_check(client, make_product):
    product = make_product(stock_qty=5)

    resp = client.post(
        "/orders",
        json={
            "customer_name": "Carol",
            "items": [
                {"product_id": product["id"], "quantity": 3},
                {"product_id": product["id"], "quantity": 3},
            ],
        },
    )
    assert resp.status_code == 400

    resp = client.get(f"/products/{product['id']}")
    assert resp.json()["stock_qty"] == 5


def test_order_against_unknown_product_is_rejected(client, make_product):
    resp = client.post(
        "/orders",
        json={"customer_name": "Dave", "items": [{"product_id": 999, "quantity": 1}]},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["problems"][0]["error"] == "product not found"


def test_cancel_order_returns_stock(client, make_product):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders",
        json={"customer_name": "Eve", "items": [{"product_id": product["id"], "quantity": 4}]},
    ).json()
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 6

    resp = client.post(f"/orders/{order['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert client.get(f"/products/{product['id']}").json()["stock_qty"] == 10


def test_cancel_already_cancelled_order_is_rejected(client, make_product):
    product = make_product(stock_qty=10)
    order = client.post(
        "/orders",
        json={"customer_name": "Frank", "items": [{"product_id": product["id"], "quantity": 1}]},
    ).json()
    client.post(f"/orders/{order['id']}/cancel")

    resp = client.post(f"/orders/{order['id']}/cancel")
    assert resp.status_code == 400


def test_cancel_unknown_order_is_404(client):
    resp = client.post("/orders/999/cancel")
    assert resp.status_code == 404


def test_price_change_does_not_affect_past_order_total(client, make_product):
    product = make_product(price=10.0, stock_qty=10)
    order = client.post(
        "/orders",
        json={"customer_name": "Grace", "items": [{"product_id": product["id"], "quantity": 2}]},
    ).json()
    assert order["total"] == 20.0

    client.put(f"/products/{product['id']}", json={"price": 50.0})

    resp = client.get(f"/orders/{order['id']}")
    assert resp.json()["total"] == 20.0
