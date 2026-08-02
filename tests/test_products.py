def test_create_and_get_product(client):
    resp = client.post("/products", json={"name": "Widget", "price": 9.99, "stock_qty": 20})
    assert resp.status_code == 201
    product = resp.json()

    resp = client.get(f"/products/{product['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Widget"


def test_get_unknown_product_is_404(client):
    resp = client.get("/products/999")
    assert resp.status_code == 404


def test_update_product(client, make_product):
    product = make_product(stock_qty=20)
    resp = client.put(f"/products/{product['id']}", json={"stock_qty": 99})
    assert resp.status_code == 200
    assert resp.json()["stock_qty"] == 99
    assert resp.json()["name"] == product["name"]


def test_delete_product(client, make_product):
    product = make_product()
    resp = client.delete(f"/products/{product['id']}")
    assert resp.status_code == 204
    assert client.get(f"/products/{product['id']}").status_code == 404


def test_low_stock_view_filters_by_threshold(client, make_product):
    make_product(name="Low", stock_qty=2)
    make_product(name="High", stock_qty=200)

    resp = client.get("/products/low-stock", params={"threshold": 10})
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Low" in names
    assert "High" not in names


def test_create_product_rejects_negative_price(client):
    resp = client.post("/products", json={"name": "Bad", "price": -5, "stock_qty": 1})
    assert resp.status_code == 422
