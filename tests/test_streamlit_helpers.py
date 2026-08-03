from app.frontend_helpers import build_order_payload, cart_total, format_currency, top_categories_with_other


def test_build_order_payload_filters_zero_quantities():
    payload = build_order_payload("Ada", {1: 2, 2: 0, 3: 5})

    assert payload == {
        "customer_name": "Ada",
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 3, "quantity": 5},
        ],
    }


def test_build_order_payload_includes_po_reference_when_given():
    payload = build_order_payload("Ada", {1: 2}, po_reference="PO-42")

    assert payload == {
        "customer_name": "Ada",
        "items": [{"product_id": 1, "quantity": 2}],
        "po_reference": "PO-42",
    }


def test_build_order_payload_includes_customer_id_when_given():
    payload = build_order_payload("Ada", {1: 2}, customer_id=7)

    assert payload == {
        "customer_name": "Ada",
        "items": [{"product_id": 1, "quantity": 2}],
        "customer_id": 7,
    }


def test_format_currency():
    assert format_currency(1234.5) == "R$ 1,234.50"
    assert format_currency(0) == "R$ 0.00"


def test_cart_total():
    cart = {1: {"price": 10.0, "quantity": 2}, 2: {"price": 5.5, "quantity": 3}}
    assert cart_total(cart) == 36.5


def test_top_categories_with_other_passthrough_under_limit():
    rows = [{"category": "A", "product_count": 1, "total_units": 1, "inventory_value": 1.0}]
    assert top_categories_with_other(rows, limit=10) == rows


def test_top_categories_with_other_folds_the_tail():
    rows = [
        {"category": f"C{i}", "product_count": 1, "total_units": 2, "inventory_value": 10.0}
        for i in range(12)
    ]
    result = top_categories_with_other(rows, limit=10)

    assert len(result) == 11
    assert result[-1] == {"category": "Other", "product_count": 2, "total_units": 4, "inventory_value": 20.0}
