def build_order_payload(
    customer_name: str,
    quantities_by_product_id: dict[int, int],
    po_reference: str | None = None,
    customer_id: int | None = None,
) -> dict:
    valid_items = [
        {"product_id": product_id, "quantity": quantity}
        for product_id, quantity in quantities_by_product_id.items()
        if quantity > 0
    ]
    payload = {"customer_name": customer_name, "items": valid_items}
    if po_reference:
        payload["po_reference"] = po_reference
    if customer_id is not None:
        payload["customer_id"] = customer_id
    return payload


def format_currency(value: float) -> str:
    return f"R$ {value:,.2f}"


def cart_total(cart: dict[int, dict]) -> float:
    return sum(item["price"] * item["quantity"] for item in cart.values())


def top_categories_with_other(rows: list[dict], limit: int = 10) -> list[dict]:
    """Fold every category past `limit` into a single "Other" bucket.

    Keeps category bar/pie charts readable when the source has dozens of
    categories (the Olist catalog has ~70) instead of drawing one bar/slice
    per category.
    """
    if len(rows) <= limit:
        return rows

    kept, rest = rows[:limit], rows[limit:]
    other = {
        "category": "Other",
        "product_count": sum(r["product_count"] for r in rest),
        "total_units": sum(r["total_units"] for r in rest),
        "inventory_value": round(sum(r["inventory_value"] for r in rest), 2),
    }
    return [*kept, other]
