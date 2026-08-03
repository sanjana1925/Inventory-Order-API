def test_create_and_get_customer(client):
    resp = client.post(
        "/customers",
        json={
            "name": "Alice Example",
            "email": "alice@example.com",
            "phone": "555-0101",
            "address": "123 Main St",
        },
    )
    assert resp.status_code == 201
    customer = resp.json()

    resp = client.get(f"/customers/{customer['id']}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


def test_get_unknown_customer_is_404(client):
    resp = client.get("/customers/999")
    assert resp.status_code == 404


def test_reports_endpoints_return_summary_data(client, make_product):
    make_product(name="Low Stock", stock_qty=2)
    make_product(name="High Stock", stock_qty=20)

    resp = client.get("/reports/low-stock")
    assert resp.status_code == 200
    assert any(item["name"] == "Low Stock" for item in resp.json())

    resp = client.get("/reports/inventory")
    assert resp.status_code == 200
    assert "total_products" in resp.json()

    resp = client.get("/reports/sales")
    assert resp.status_code == 200
    assert "total_orders" in resp.json()
