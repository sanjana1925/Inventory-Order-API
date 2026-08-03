import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.frontend_helpers import build_order_payload, cart_total, format_currency, top_categories_with_other

API_BASE_URL = "http://127.0.0.1:8000"

# Single-series bars/lines get one flat color rather than a per-bar rainbow —
# there's no second dimension being encoded, the axis labels already carry identity.
ACCENT = "#3b82f6"
ACCENT_SOFT = "#60a5fa"
ORDER_STATUS_FLOW = ["pending", "processing", "shipped", "delivered", "completed"]

# Inline SVG (no external file/network dependency) for the client dashboard banner.
DASHBOARD_HERO_SVG = """
<svg width="130" height="110" viewBox="0 0 130 110" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="100" cy="30" r="22" fill="#3b82f6" opacity="0.15"/>
  <circle cx="20" cy="20" r="10" fill="#60a5fa" opacity="0.2"/>
  <path d="M15 48 L65 20 L115 48 L65 76 Z" fill="#1e293b" stroke="#60a5fa" stroke-width="2"/>
  <path d="M15 48 V78 L65 106 V76 Z" fill="#111827" stroke="#334155" stroke-width="2"/>
  <path d="M115 48 V78 L65 106 V76 Z" fill="#0f172a" stroke="#334155" stroke-width="2"/>
  <path d="M40 34 L90 62" stroke="#3b82f6" stroke-width="2" opacity="0.6"/>
</svg>
"""

ADMIN_HERO_SVG = """
<svg width="130" height="110" viewBox="0 0 130 110" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="105" cy="25" r="18" fill="#60a5fa" opacity="0.15"/>
  <rect x="12" y="14" width="106" height="80" rx="10" fill="#1e293b" stroke="#334155" stroke-width="2"/>
  <line x1="20" y1="80" x2="110" y2="80" stroke="#334155" stroke-width="2"/>
  <rect x="30" y="58" width="12" height="22" rx="2" fill="#3b82f6"/>
  <rect x="50" y="44" width="12" height="36" rx="2" fill="#60a5fa"/>
  <rect x="70" y="64" width="12" height="16" rx="2" fill="#3b82f6" opacity="0.7"/>
  <rect x="90" y="32" width="12" height="48" rx="2" fill="#60a5fa" opacity="0.9"/>
  <path d="M30 40 L52 26 L74 34 L102 18" stroke="#93c5fd" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>
"""

st.set_page_config(page_title="Inventory & Order Management", page_icon="\U0001F4E6", layout="wide")
px.defaults.template = "plotly_dark"

st.markdown(
    """
    <style>
    .stApp { background: #020617; color: #f8fafc; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #111827 100%); }
    .metric-card {
        background: linear-gradient(135deg, #111827 0%, #1e293b 100%);
        border: 1px solid #334155; border-radius: 16px; padding: 1rem 1.2rem;
        margin-bottom: 0.8rem; box-shadow: 0 8px 24px rgba(2,6,23,0.35);
    }
    .metric-card h4 { margin: 0 0 0.25rem 0; color: #93c5fd; font-size: 0.9rem; }
    .metric-card h2 { margin: 0; color: #f8fafc; font-size: 1.45rem; }
    .metric-card p { margin: 0.2rem 0 0; color: #cbd5e1; font-size: 0.86rem; }
    .stTextInput > div > div > input, .stNumberInput input, .stSelectbox > div > div {
        background: #0f172a; color: #f8fafc; border: 1px solid #334155; border-radius: 8px;
    }
    .stButton > button { background: #2563eb; color: white; border: none; border-radius: 10px; }
    .stButton > button:hover { background: #1d4ed8; }
    .stDataFrame, .stTable { background: #0f172a; }
    .hero-banner {
        display: flex; align-items: center; justify-content: space-between; gap: 1rem;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155; border-radius: 18px; padding: 1.4rem 1.8rem;
        margin-bottom: 1.2rem; box-shadow: 0 8px 24px rgba(2,6,23,0.35);
    }
    .hero-banner h2 { margin: 0 0 0.3rem 0; color: #f8fafc; font-size: 1.5rem; }
    .hero-banner p { margin: 0; color: #94a3b8; font-size: 0.95rem; }
    .low-stock-critical, .low-stock-warning {
        border-radius: 8px; padding: 0.35rem 0.6rem; margin-bottom: 0.3rem;
    }
    .low-stock-critical { border-left: 3px solid #f87171; background: rgba(248,113,113,0.10); }
    .low-stock-warning { border-left: 3px solid #fb923c; background: rgba(251,146,60,0.08); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

DEFAULTS = {
    "role": None,
    "customer": None,
    "admin_user": None,
    "active_view": None,
    "cart": {},
    "auth_error": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value
for key in ("products_skip", "orders_skip", "customers_skip", "suppliers_skip", "purchase_orders_skip"):
    if key not in st.session_state:
        st.session_state[key] = 0

CLIENT_MENU = [
    "Dashboard", "Catalog", "Purchase Orders", "My Orders",
    "Notifications", "Company Profile", "Delivery Addresses",
]
ADMIN_MENU = [
    "Dashboard", "Products", "Categories", "Inventory", "Orders",
    "Suppliers", "Purchase Orders", "Customers", "Users",
    "Reports", "Notifications", "Profile Settings",
]
MENU_ICONS = {
    "Dashboard": "\U0001F3E0", "Catalog": "\U0001F6D2", "Purchase Orders": "\U0001F4DD",
    "My Orders": "\U0001F9FE", "Notifications": "\U0001F514", "Company Profile": "\U0001F3E2",
    "Delivery Addresses": "\U0001F4CD", "Products": "\U0001F4E6", "Categories": "\U0001F5C2\U0000FE0F",
    "Inventory": "\U0001F3EC", "Orders": "\U0001F9FE", "Suppliers": "\U0001F69A",
    "Customers": "\U0001F465", "Users": "\U0001F9D1‍\U0001F4BC", "Reports": "\U0001F4C8",
    "Profile Settings": "\U00002699\U0000FE0F",
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get_list(path: str, params: dict | None = None) -> tuple[list[dict], int]:
    try:
        response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=10)
        response.raise_for_status()
        total = int(response.headers.get("X-Total-Count", len(response.json())))
        return response.json(), total
    except requests.RequestException as exc:
        st.error(f"Could not reach the API at {API_BASE_URL}: {exc}")
        return [], 0


@st.cache_data(show_spinner=False, ttl=30)
def api_get_cached(path: str):
    try:
        response = requests.get(f"{API_BASE_URL}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}


def api_post(path: str, json: dict, timeout: int = 10):
    return requests.post(f"{API_BASE_URL}{path}", json=json, timeout=timeout)


def clamp_page(skip_key: str, rows: list, total: int):
    if not rows and total > 0 and st.session_state[skip_key] != 0:
        st.session_state[skip_key] = 0
        st.rerun()


def pager(label: str, skip_key: str, total: int, page_size: int):
    page = st.session_state[skip_key] // page_size + 1
    pages = max(1, -(-total // page_size))
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("Previous", disabled=page <= 1, key=f"{skip_key}_prev"):
            st.session_state[skip_key] = max(0, st.session_state[skip_key] - page_size)
            st.rerun()
    with c2:
        st.caption(f"{label}: page {page} of {pages} — {total:,} total")
    with c3:
        if st.button("Next", disabled=page >= pages, key=f"{skip_key}_next"):
            st.session_state[skip_key] += page_size
            st.rerun()


def clear_all_state_for_logout():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    for key in ("products_skip", "orders_skip", "customers_skip", "suppliers_skip", "purchase_orders_skip"):
        st.session_state[key] = 0
    # The admin PO builder cart lives outside DEFAULTS — clear it explicitly
    # so it doesn't bleed into the next login.
    st.session_state.admin_po_cart = {}
    api_get_cached.clear()


# ---------------------------------------------------------------------------
# Landing / auth gate
# ---------------------------------------------------------------------------

if st.session_state.role is None:
    st.markdown(
        """
        <div style='text-align:center; padding: 2.5rem 0 1rem;'>
        <h1>\U0001F4E6 Inventory & Order Management</h1>
        <p style='color:#94a3b8;'>A business client portal for placing and tracking purchase orders.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, center, _ = st.columns([1, 2, 1])
    with center:
        tab_client, tab_admin = st.tabs(["Business client", "Admin / staff"])

        with tab_client:
            login_tab, signup_tab = st.tabs(["Log in", "Sign up"])
            with login_tab:
                with st.form("client_login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Log in", use_container_width=True):
                        resp = api_post("/customers/login", {"email": email, "password": password})
                        if resp.status_code == 200:
                            st.session_state.role = "client"
                            st.session_state.customer = resp.json()
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Login failed"))
            with signup_tab:
                with st.form("client_signup_form"):
                    name = st.text_input("Company / contact name")
                    s_email = st.text_input("Email", key="signup_email")
                    s_password = st.text_input("Password", type="password", key="signup_password")
                    phone = st.text_input("Phone (optional)")
                    if st.form_submit_button("Create account", use_container_width=True):
                        if not name or not s_email or len(s_password) < 6:
                            st.warning("Name, email, and a password (6+ characters) are required")
                        else:
                            resp = api_post(
                                "/customers/signup",
                                {"name": name, "email": s_email, "password": s_password, "phone": phone or None},
                            )
                            if resp.status_code == 201:
                                st.session_state.role = "client"
                                st.session_state.customer = resp.json()
                                st.rerun()
                            else:
                                st.error(resp.json().get("detail", "Could not create account"))

        with tab_admin:
            with st.form("admin_login_form"):
                a_email = st.text_input("Email", key="admin_email")
                a_password = st.text_input("Password", type="password", key="admin_password")
                if st.form_submit_button("Log in", use_container_width=True):
                    resp = api_post("/auth/login", {"email": a_email, "password": a_password})
                    if resp.status_code == 200:
                        st.session_state.role = "admin"
                        st.session_state.admin_user = resp.json()
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Login failed"))
    st.stop()

ACTIVE_MENU = ADMIN_MENU if st.session_state.role == "admin" else CLIENT_MENU
if st.session_state.active_view not in ACTIVE_MENU:
    st.session_state.active_view = ACTIVE_MENU[0]

identity = st.session_state.admin_user if st.session_state.role == "admin" else st.session_state.customer
customer_name = st.session_state.customer["name"] if st.session_state.customer else None
customer_id = st.session_state.customer["id"] if st.session_state.customer else None

with st.sidebar:
    st.markdown("### \U0001F3E2 Inventory & Order Management")
    st.caption(f"Signed in as **{identity['email']}** ({st.session_state.role})")

    choice = st.radio(
        "Navigation", ACTIVE_MENU, index=ACTIVE_MENU.index(st.session_state.active_view),
        format_func=lambda x: f"{MENU_ICONS.get(x, '')}  {x}", label_visibility="collapsed",
    )
    st.session_state.active_view = choice

    st.markdown("---")
    if st.button("\U0001F504 Refresh data", use_container_width=True):
        api_get_cached.clear()
        st.rerun()
    if st.button("\U0001F6AA Log out", use_container_width=True):
        clear_all_state_for_logout()
        st.rerun()

st.markdown(
    f"""
    <div style='padding: 0.2rem 0 0.8rem 0;'>
    <h1 style='margin:0; font-size:1.9rem;'>{MENU_ICONS.get(st.session_state.active_view, '')} {st.session_state.active_view}</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

view = st.session_state.active_view

# ===========================================================================
# CLIENT VIEWS
# ===========================================================================

if st.session_state.role == "client":

    if view == "Dashboard":
        my_orders, my_total = api_get_list("/orders", {"customer_id": customer_id, "limit": 5})
        notifs = api_get_cached("/notifications?audience=client&limit=5")

        st.markdown(
            f"""
            <div class='hero-banner'>
                <div>
                    <h2>Welcome back, {customer_name or "there"} \U0001F44B</h2>
                    <p>Here's a quick look at your account — browse the catalog, track orders, and manage your profile.</p>
                </div>
                {DASHBOARD_HERO_SVG}
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='metric-card'><h4>My orders</h4><h2>{my_total:,}</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><h4>Notifications</h4><h2>{len(notifs):,}</h2></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("\U0001F9FE Recent orders")
        if my_orders:
            df = pd.DataFrame(my_orders)[["id", "created_at", "status", "total"]]
            df["total"] = df["total"].map(format_currency)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No purchase orders yet — place one from the Purchase Orders page.")

        st.markdown("---")
        st.subheader("\U0001F4E9 Need help?")
        sc1, sc2 = st.columns([2, 1])
        with sc1:
            with st.form("client_complaint_form", clear_on_submit=True):
                subject = st.text_input("Subject")
                message = st.text_area("Describe the issue")
                if st.form_submit_button("Submit complaint"):
                    if subject and message:
                        resp = api_post(
                            "/support",
                            {
                                "customer_name": customer_name,
                                "customer_id": customer_id,
                                "email": st.session_state.customer["email"],
                                "subject": subject,
                                "message": message,
                            },
                        )
                        if resp.status_code == 201:
                            st.success("Complaint submitted — our support team will follow up by email.")
                            api_get_cached.clear()
                        else:
                            st.error(resp.json().get("detail", "Could not submit complaint"))
                    else:
                        st.warning("Subject and message are required")

            my_complaints = api_get_cached(f"/support?customer_id={customer_id}")
            if my_complaints:
                st.caption("Your recent complaints")
                df = pd.DataFrame(my_complaints[:5])[["id", "subject", "status", "created_at"]]
                st.dataframe(df, use_container_width=True, hide_index=True)
        with sc2:
            st.markdown(
                """
                <div class='metric-card' style='text-align:center;'>
                <h4>Call support</h4>
                <a href='tel:+18005550199' style='font-size:1.25rem; text-decoration:none; color:#93c5fd;'>
                \U0001F4DE +1 (800) 555-0199</a>
                <p>Mon–Fri, 9am–6pm</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    elif view == "Catalog":
        st.subheader("\U0001F6D2 Product catalog")
        categories = api_get_cached("/products/categories")
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("Search products")
        with c2:
            category_filter = st.selectbox("Category", ["All", *categories]) if categories else "All"

        page_size = 25
        params = {"skip": st.session_state.products_skip, "limit": page_size}
        if search:
            params["q"] = search
        if category_filter and category_filter != "All":
            params["category"] = category_filter

        rows, total = api_get_list("/products", params)
        clamp_page("products_skip", rows, total)
        pager("Products", "products_skip", total, page_size)

        for product in rows:
            with st.expander(f"{product['name']} — {format_currency(product['price'])} ({product['stock_qty']} in stock)"):
                st.write(f"Category: {product['category'] or 'Uncategorized'}")
                st.write("In stock" if product["stock_qty"] > 0 else "Out of stock")
                qty = st.number_input("Quantity", min_value=1, max_value=max(1, product["stock_qty"]), value=1, key=f"cat_qty_{product['id']}")
                if st.button("Add to purchase order", key=f"cat_add_{product['id']}"):
                    st.session_state.cart[product["id"]] = {"name": product["name"], "price": product["price"], "quantity": qty}
                    st.success("Added to cart — see Purchase Orders")

    elif view == "Purchase Orders":
        st.subheader("\U0001F4DD Create a purchase order")

        st.markdown("##### Reorder a previous purchase")
        past_orders, _ = api_get_list("/orders", {"customer_id": customer_id, "limit": 20})
        if past_orders:
            options = {f"Order #{o['id']} ({o['created_at'][:10]}, {format_currency(o['total'])})": o["id"] for o in past_orders}
            choice = st.selectbox("Load items from a past order", ["—", *options.keys()])
            if choice != "—" and st.button("Load into cart"):
                order = api_get_cached(f"/orders/{options[choice]}")
                if order:
                    for item in order["items"]:
                        st.session_state.cart[item["product_id"]] = {
                            "name": item["product_name"], "price": item["unit_price"], "quantity": item["quantity"],
                        }
                    st.success("Cart loaded")
                    st.rerun()

        st.markdown("##### Add products")
        search = st.text_input("Search products to add", key="po_search")
        if search:
            matches, _ = api_get_list("/products", {"q": search, "limit": 10})
            for product in matches:
                c1, c2, c3 = st.columns([4, 2, 1])
                c1.write(f"**{product['name']}** — {format_currency(product['price'])} ({product['stock_qty']} in stock)")
                qty = c2.number_input("Qty", min_value=1, max_value=max(1, product["stock_qty"]), value=1, key=f"po_qty_{product['id']}", label_visibility="collapsed")
                if c3.button("Add", key=f"po_add_{product['id']}"):
                    st.session_state.cart[product["id"]] = {"name": product["name"], "price": product["price"], "quantity": qty}
                    st.rerun()

        st.markdown("#### Cart")
        if st.session_state.cart:
            cart_df = pd.DataFrame([
                {"Product": item["name"], "Qty": item["quantity"], "Unit price": format_currency(item["price"]),
                 "Line total": format_currency(item["price"] * item["quantity"])}
                for item in st.session_state.cart.values()
            ])
            st.dataframe(cart_df, use_container_width=True, hide_index=True)
            st.markdown(f"**Total: {format_currency(cart_total(st.session_state.cart))}**")

            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                po_reference = st.text_input("Your PO reference (optional)")
            with c2:
                if st.button("Clear cart"):
                    st.session_state.cart = {}
                    st.rerun()
            with c3:
                if st.button("Submit purchase order", type="primary"):
                    quantities = {pid: item["quantity"] for pid, item in st.session_state.cart.items()}
                    payload = build_order_payload(customer_name, quantities, po_reference, customer_id)
                    resp = api_post("/orders", payload)
                    if resp.status_code == 201:
                        st.success(f"Order #{resp.json()['id']} placed")
                        st.session_state.cart = {}
                        api_get_cached.clear()
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Could not place order"))
        else:
            st.info("Search for a product above, or reorder from a past purchase.")

    elif view == "My Orders":
        st.subheader("\U0001F553 Purchase history")
        status_filter = st.selectbox("Status", ["All", *ORDER_STATUS_FLOW, "cancelled"])
        page_size = 20
        params = {"customer_id": customer_id, "skip": st.session_state.orders_skip, "limit": page_size}
        if status_filter != "All":
            params["status"] = status_filter

        orders, total = api_get_list("/orders", params)
        clamp_page("orders_skip", orders, total)
        pager("Orders", "orders_skip", total, page_size)

        for order in orders:
            title = f"#{order['id']} — {order['created_at'][:10]} — {format_currency(order['total'])} — {order['status']}"
            if order.get("po_reference"):
                title += f" — PO {order['po_reference']}"
            with st.expander(title):
                items_df = pd.DataFrame(order["items"])[["product_name", "quantity", "unit_price", "line_total"]]
                items_df.columns = ["Product", "Qty", "Unit price", "Line total"]
                items_df["Unit price"] = items_df["Unit price"].map(format_currency)
                items_df["Line total"] = items_df["Line total"].map(format_currency)
                st.dataframe(items_df, use_container_width=True, hide_index=True)

                progress = ORDER_STATUS_FLOW.index(order["status"]) + 1 if order["status"] in ORDER_STATUS_FLOW else 0
                st.progress(progress / len(ORDER_STATUS_FLOW) if order["status"] != "cancelled" else 0.0)

                c1, c2 = st.columns(2)
                with c1:
                    invoice = requests.get(f"{API_BASE_URL}/orders/{order['id']}/invoice", timeout=10)
                    if invoice.status_code == 200:
                        st.download_button("Download invoice", invoice.content, file_name=f"invoice-{order['id']}.pdf", mime="application/pdf", key=f"inv_{order['id']}")
                with c2:
                    if order["status"] == "pending":
                        if st.button("Cancel order", key=f"cancel_{order['id']}"):
                            resp = api_post(f"/orders/{order['id']}/cancel", {})
                            if resp.status_code == 200:
                                st.success("Order cancelled")
                                api_get_cached.clear()
                                st.rerun()

    elif view == "Notifications":
        st.subheader("\U0001F514 Notifications")
        notifs = api_get_cached("/notifications?audience=client&limit=50")
        if notifs:
            df = pd.DataFrame(notifs)[["created_at", "message", "level"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No notifications yet.")

    elif view == "Company Profile":
        st.subheader("\U0001F3E2 Company profile")
        c = st.session_state.customer
        with st.form("profile_form"):
            name = st.text_input("Company / contact name", value=c["name"])
            phone = st.text_input("Phone", value=c.get("phone") or "")
            address = st.text_input("Primary address", value=c.get("address") or "")
            if st.form_submit_button("Save changes"):
                resp = requests.put(f"{API_BASE_URL}/customers/{c['id']}", json={"name": name, "phone": phone or None, "address": address or None}, timeout=10)
                if resp.status_code == 200:
                    st.session_state.customer = resp.json()
                    st.success("Profile updated")
                    st.rerun()
                else:
                    st.error("Could not update profile")

    elif view == "Delivery Addresses":
        st.subheader("\U0001F4CD Delivery addresses")
        c = st.session_state.customer
        with st.form("address_form"):
            label = st.text_input("Label (e.g. Warehouse, HQ)")
            address = st.text_input("Address")
            is_default = st.checkbox("Set as default")
            if st.form_submit_button("Add address"):
                if label and address:
                    resp = api_post(f"/customers/{c['id']}/addresses", {"label": label, "address": address, "is_default": is_default})
                    if resp.status_code == 201:
                        st.success("Address added")
                        st.rerun()
                else:
                    st.warning("Label and address are required")

        addresses = api_get_cached(f"/customers/{c['id']}/addresses")
        if addresses:
            df = pd.DataFrame(addresses)[["label", "address", "is_default"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
            for a in addresses:
                if st.button(f"Delete '{a['label']}'", key=f"del_addr_{a['id']}"):
                    requests.delete(f"{API_BASE_URL}/customers/{c['id']}/addresses/{a['id']}", timeout=5)
                    api_get_cached.clear()
                    st.rerun()


# ===========================================================================
# ADMIN VIEWS
# ===========================================================================

elif st.session_state.role == "admin":

    if view == "Dashboard":
        overview = api_get_cached("/reports/overview")

        st.markdown(
            f"""
            <div class='hero-banner'>
                <div>
                    <h2>Welcome back, {identity['email']} \U0001F4CA</h2>
                    <p>Here's the current state of the business — inventory, orders, and revenue at a glance.</p>
                </div>
                {ADMIN_HERO_SVG}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not overview:
            st.info("No data yet — seed the database and refresh.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"<div class='metric-card'><h4>Products</h4><h2>{overview['total_products']:,}</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><h4>Orders</h4><h2>{overview['total_orders']:,}</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'><h4>Customers</h4><h2>{overview['total_customers']:,}</h2></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='metric-card'><h4>Revenue</h4><h2>{format_currency(overview['total_revenue'])}</h2></div>", unsafe_allow_html=True)

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("\U000026A0\U0000FE0F Low stock")
                low_stock = api_get_cached("/reports/low-stock?limit=8")
                if low_stock:
                    st.caption("Sorted worst-first — restock the top items first.")
                    for p in low_stock:
                        critical = p["stock_qty"] <= 3
                        css_class = "low-stock-critical" if critical else "low-stock-warning"
                        dot = "\U0001F534" if critical else "\U0001F7E0"
                        lc1, lc2, lc3 = st.columns([3, 2, 1.3])
                        lc1.markdown(
                            f"""<div class='{css_class}'>{dot} <b>{p['name']}</b><br>
                            <span style='color:#94a3b8;font-size:0.8rem;'>{p['category'] or 'Uncategorized'} — {p['stock_qty']} left</span></div>""",
                            unsafe_allow_html=True,
                        )
                        restock_qty = lc2.number_input(
                            "Restock by", min_value=1, value=50, step=10,
                            key=f"dash_restock_qty_{p['id']}", label_visibility="collapsed",
                        )
                        if lc3.button("Restock", key=f"dash_restock_{p['id']}", use_container_width=True):
                            resp = requests.put(
                                f"{API_BASE_URL}/products/{p['id']}",
                                json={"stock_qty": p["stock_qty"] + restock_qty},
                                timeout=10,
                            )
                            if resp.status_code == 200:
                                st.success(f"Restocked {p['name']}")
                                api_get_cached.clear()
                                st.rerun()
                            else:
                                st.error(resp.json().get("detail", "Could not restock"))
                else:
                    st.caption("Nothing low on stock right now.")
            with c2:
                st.subheader("\U0001F9FE Recent orders")
                recent, _ = api_get_list("/orders", {"limit": 8})
                if recent:
                    df = pd.DataFrame(recent)[["id", "customer_name", "status", "total"]]
                    df["total"] = df["total"].map(format_currency)
                    st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("\U00002705 Delivered — awaiting completion")
            delivered_orders, delivered_total = api_get_list("/orders", {"status": "delivered", "limit": 10})
            if delivered_orders:
                st.caption(f"{delivered_total:,} order(s) delivered and ready to be marked complete")
                for order in delivered_orders:
                    oc1, oc2 = st.columns([4, 1])
                    oc1.write(f"#{order['id']} — {order['customer_name']} — {format_currency(order['total'])}")
                    with oc2:
                        if st.button("Mark completed", key=f"dash_complete_{order['id']}", use_container_width=True):
                            resp = requests.patch(
                                f"{API_BASE_URL}/orders/{order['id']}/status", json={"status": "completed"}, timeout=10
                            )
                            if resp.status_code == 200:
                                api_get_cached.clear()
                                st.rerun()
                            else:
                                st.error(resp.json().get("detail", "Could not update status"))
            else:
                st.caption("No delivered orders waiting on completion.")

    elif view == "Products":
        st.subheader("\U0001F4E6 Manage products")
        with st.expander("Add product"):
            categories = api_get_cached("/products/categories")
            with st.form("create_product_form"):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    name = st.text_input("Product name")
                with c2:
                    category = st.selectbox("Category", ["", *categories])
                with c3:
                    price = st.number_input("Price", min_value=0.01, step=0.01)
                with c4:
                    stock_qty = st.number_input("Stock", min_value=0, step=1)
                if st.form_submit_button("Add product", use_container_width=True):
                    if not name:
                        st.warning("Please enter the product name")
                    else:
                        payload = {"name": name, "price": price, "stock_qty": stock_qty}
                        if category:
                            payload["category"] = category
                        resp = api_post("/products", payload)
                        if resp.status_code == 201:
                            st.success("Product created")
                            api_get_cached.clear()
                        else:
                            st.error(resp.json().get("detail", "Could not create product"))

        categories = api_get_cached("/products/categories")
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("Search by name")
        with c2:
            category_filter = st.selectbox("Category filter", ["All", *categories]) if categories else "All"

        page_size = 25
        params = {"skip": st.session_state.products_skip, "limit": page_size}
        if search:
            params["q"] = search
        if category_filter and category_filter != "All":
            params["category"] = category_filter

        rows, total = api_get_list("/products", params)
        clamp_page("products_skip", rows, total)
        pager("Products", "products_skip", total, page_size)

        for p in rows:
            with st.expander(f"#{p['id']} {p['name']} — {format_currency(p['price'])} — stock {p['stock_qty']}"):
                with st.form(f"edit_product_{p['id']}"):
                    c1, c2, c3 = st.columns(3)
                    new_price = c1.number_input("Price", min_value=0.01, value=float(p["price"]), key=f"price_{p['id']}")
                    new_stock = c2.number_input("Stock", min_value=0, value=int(p["stock_qty"]), key=f"stock_{p['id']}")
                    new_category = c3.text_input("Category", value=p["category"] or "", key=f"cat_{p['id']}")
                    c4, c5 = st.columns(2)
                    save = c4.form_submit_button("Save")
                    delete = c5.form_submit_button("Delete")
                    if save:
                        resp = requests.put(f"{API_BASE_URL}/products/{p['id']}", json={"price": new_price, "stock_qty": new_stock, "category": new_category or None}, timeout=10)
                        if resp.status_code == 200:
                            st.success("Saved")
                            api_get_cached.clear()
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Could not save"))
                    if delete:
                        resp = requests.delete(f"{API_BASE_URL}/products/{p['id']}", timeout=10)
                        if resp.status_code == 204:
                            st.success("Deleted")
                            api_get_cached.clear()
                            st.rerun()
                        else:
                            st.error("Could not delete (likely referenced by existing orders)")

    elif view == "Categories":
        st.subheader("\U0001F5C2\U0000FE0F Manage categories")
        with st.form("add_category_form"):
            name = st.text_input("Category name")
            if st.form_submit_button("Add category"):
                if name:
                    resp = api_post("/categories", {"name": name})
                    if resp.status_code == 201:
                        st.success("Category added")
                        api_get_cached.clear()
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Could not add category"))

        cats = api_get_cached("/categories")
        if cats:
            for cat in cats:
                c1, c2 = st.columns([4, 1])
                c1.write(cat["name"])
                if c2.button("Delete", key=f"del_cat_{cat['id']}"):
                    requests.delete(f"{API_BASE_URL}/categories/{cat['id']}", timeout=5)
                    api_get_cached.clear()
                    st.rerun()

    elif view == "Inventory":
        st.subheader("\U0001F3EC Inventory")
        inv = api_get_cached("/reports/inventory")
        if inv:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total products", f"{inv['total_products']:,}")
            c2.metric("Units in stock", f"{inv['total_units']:,}")
            c3.metric("Low stock (<10)", f"{inv['low_stock_count']:,}")
            c4.metric("Inventory value", format_currency(inv["inventory_value"]))

            st.markdown("---")
            category_mix = api_get_cached("/reports/category-mix")
            if category_mix:
                folded = top_categories_with_other(category_mix, limit=10)
                cat_df = pd.DataFrame(folded).sort_values("inventory_value")
                fig = px.bar(cat_df, x="inventory_value", y="category", orientation="h", title="Inventory value by category")
                fig.update_traces(marker_color=ACCENT)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("\U0001F504 Update stock")
        search = st.text_input("Search product to adjust stock")
        if search:
            matches, _ = api_get_list("/products", {"q": search, "limit": 10})
            for p in matches:
                c1, c2, c3 = st.columns([4, 2, 1])
                c1.write(f"{p['name']} (current: {p['stock_qty']})")
                new_qty = c2.number_input("New stock", min_value=0, value=int(p["stock_qty"]), key=f"adj_{p['id']}", label_visibility="collapsed")
                if c3.button("Update", key=f"adjbtn_{p['id']}"):
                    resp = requests.put(f"{API_BASE_URL}/products/{p['id']}", json={"stock_qty": new_qty}, timeout=10)
                    if resp.status_code == 200:
                        st.success("Updated")
                        api_get_cached.clear()
                        st.rerun()

        st.markdown("---")
        st.subheader("\U000026A0\U0000FE0F Low-stock detail")
        threshold = st.slider("Threshold", min_value=1, max_value=50, value=10)
        low_stock, low_total = api_get_list("/reports/low-stock", {"threshold": threshold, "limit": 100})
        st.caption(f"{low_total:,} products below the threshold — showing up to 100")
        if low_stock:
            df = pd.DataFrame(low_stock)[["id", "name", "category", "stock_qty", "price"]]
            df.columns = ["ID", "Name", "Category", "Stock", "Price"]
            df["Price"] = df["Price"].map(format_currency)
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif view == "Orders":
        st.subheader("\U0001F9FE Manage orders")
        c1, c2 = st.columns([2, 1])
        with c1:
            customer_filter = st.text_input("Filter by customer")
        with c2:
            status_filter = st.selectbox("Status", ["All", *ORDER_STATUS_FLOW, "cancelled"])

        page_size = 25
        params = {"skip": st.session_state.orders_skip, "limit": page_size}
        if customer_filter:
            params["customer"] = customer_filter
        if status_filter != "All":
            params["status"] = status_filter

        orders, total = api_get_list("/orders", params)
        clamp_page("orders_skip", orders, total)
        pager("Orders", "orders_skip", total, page_size)

        for order in orders:
            title = f"#{order['id']} — {order['customer_name']} — {format_currency(order['total'])} — {order['status']}"
            with st.expander(title):
                items_df = pd.DataFrame(order["items"])[["product_name", "quantity", "unit_price", "line_total"]]
                items_df.columns = ["Product", "Qty", "Unit price", "Line total"]
                st.dataframe(items_df, use_container_width=True, hide_index=True)
                st.caption(f"Placed {order['created_at']}" + (f" — PO {order['po_reference']}" if order.get("po_reference") else ""))

                if order["status"] in ("pending", "processing", "shipped", "delivered"):
                    next_status = {
                        "pending": "processing", "processing": "shipped",
                        "shipped": "delivered", "delivered": "completed",
                    }[order["status"]]
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"Advance to {next_status}", key=f"advance_{order['id']}"):
                            resp = requests.patch(f"{API_BASE_URL}/orders/{order['id']}/status", json={"status": next_status}, timeout=10)
                            if resp.status_code == 200:
                                api_get_cached.clear()
                                st.rerun()
                            else:
                                st.error(resp.json().get("detail", "Could not update status"))
                    with c2:
                        if order["status"] in ("pending", "processing"):
                            if st.button("Cancel order", key=f"admin_cancel_{order['id']}"):
                                resp = api_post(f"/orders/{order['id']}/cancel", {})
                                if resp.status_code == 200:
                                    api_get_cached.clear()
                                    st.rerun()

    elif view == "Suppliers":
        st.subheader("\U0001F69A Suppliers")
        with st.form("add_supplier_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name")
            city = c2.text_input("City")
            state = c3.text_input("State")
            if st.form_submit_button("Add supplier"):
                if name:
                    resp = api_post("/suppliers", {"name": name, "city": city or None, "state": state or None})
                    if resp.status_code == 201:
                        st.success("Supplier added")
                        api_get_cached.clear()
                        st.rerun()

        search = st.text_input("Search suppliers")
        page_size = 25
        params = {"skip": st.session_state.suppliers_skip, "limit": page_size}
        if search:
            params["q"] = search
        rows, total = api_get_list("/suppliers", params)
        clamp_page("suppliers_skip", rows, total)
        pager("Suppliers", "suppliers_skip", total, page_size)
        if rows:
            df = pd.DataFrame(rows)[["id", "name", "city", "state"]]
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif view == "Purchase Orders":
        st.subheader("\U0001F4DD Procurement purchase orders")

        with st.expander("Create purchase order"):
            supplier_search = st.text_input("Search suppliers", key="po_supplier_search")
            supplier_options = {}
            if supplier_search:
                matches, _ = api_get_list("/suppliers", {"q": supplier_search, "limit": 10})
                supplier_options = {s["name"]: s["id"] for s in matches}
            supplier_choice = st.selectbox("Supplier", list(supplier_options.keys())) if supplier_options else None

            search = st.text_input("Search products to order", key="po_admin_search")
            if "admin_po_cart" not in st.session_state:
                st.session_state.admin_po_cart = {}
            if search:
                matches, _ = api_get_list("/products", {"q": search, "limit": 10})
                for p in matches:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.write(p["name"])
                    qty = c2.number_input("Qty", min_value=1, value=1, key=f"admpo_qty_{p['id']}", label_visibility="collapsed")
                    cost = c3.number_input("Unit cost", min_value=0.01, value=float(p["price"]) * 0.6, key=f"admpo_cost_{p['id']}", label_visibility="collapsed")
                    if c4.button("Add", key=f"admpo_add_{p['id']}"):
                        st.session_state.admin_po_cart[p["id"]] = {"name": p["name"], "quantity": qty, "unit_cost": cost}
                        st.rerun()

            if st.session_state.admin_po_cart:
                df = pd.DataFrame([{"Product": v["name"], "Qty": v["quantity"], "Unit cost": v["unit_cost"]} for v in st.session_state.admin_po_cart.values()])
                st.dataframe(df, use_container_width=True, hide_index=True)
                if st.button("Submit purchase order") and supplier_choice:
                    items = [{"product_id": pid, "quantity": v["quantity"], "unit_cost": v["unit_cost"]} for pid, v in st.session_state.admin_po_cart.items()]
                    resp = api_post("/purchase-orders", {"supplier_id": supplier_options[supplier_choice], "items": items})
                    if resp.status_code == 201:
                        st.success(f"Purchase order #{resp.json()['id']} created")
                        st.session_state.admin_po_cart = {}
                        api_get_cached.clear()
                        st.rerun()

        po_page_size = 20
        pos, po_total = api_get_list("/purchase-orders", {"skip": st.session_state.purchase_orders_skip, "limit": po_page_size})
        clamp_page("purchase_orders_skip", pos, po_total)
        pager("Purchase orders", "purchase_orders_skip", po_total, po_page_size)
        for po in pos:
            with st.expander(f"PO #{po['id']} — {po['supplier_name']} — {po['status']} — {format_currency(po['total_cost'])}"):
                df = pd.DataFrame(po["items"])
                st.dataframe(df, use_container_width=True, hide_index=True)
                if po["status"] != "received":
                    if st.button("Receive stock", key=f"receive_{po['id']}"):
                        resp = api_post(f"/purchase-orders/{po['id']}/receive", {})
                        if resp.status_code == 200:
                            st.success("Stock received")
                            api_get_cached.clear()
                            st.rerun()

    elif view == "Customers":
        st.subheader("\U0001F465 Customers")
        search = st.text_input("Search by name or email", key="customer_search")
        page_size = 25
        params = {"skip": st.session_state.customers_skip, "limit": page_size}
        if search:
            params["q"] = search
        rows, total = api_get_list("/customers", params)
        clamp_page("customers_skip", rows, total)
        pager("Customers", "customers_skip", total, page_size)
        if rows:
            df = pd.DataFrame(rows)[["id", "name", "email", "phone", "address"]]
            df.columns = ["ID", "Name", "Email", "Phone", "Address"]
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif view == "Users":
        st.subheader("\U0001F9D1‍\U0001F4BC Admin & staff users")
        with st.form("add_user_form"):
            c1, c2, c3 = st.columns(3)
            email = c1.text_input("Email")
            password = c2.text_input("Password", type="password")
            role = c3.selectbox("Role", ["staff", "admin"])
            if st.form_submit_button("Add user"):
                if email and len(password) >= 6:
                    resp = api_post("/users", {"email": email, "password": password, "role": role})
                    if resp.status_code == 201:
                        st.success("User created")
                        api_get_cached.clear()
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Could not create user"))
                else:
                    st.warning("Email and a password (6+ characters) are required")

        users = api_get_cached("/users")
        if users:
            df = pd.DataFrame(users)[["id", "email", "role"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
            for u in users:
                if st.button(f"Delete {u['email']}", key=f"del_user_{u['id']}"):
                    requests.delete(f"{API_BASE_URL}/users/{u['id']}", timeout=5)
                    api_get_cached.clear()
                    st.rerun()

    elif view == "Reports":
        tab1, tab2 = st.tabs(["Sales reports", "Inventory reports"])
        with tab1:
            top_products = api_get_cached("/reports/top-products?limit=10")
            if top_products:
                tp_df = pd.DataFrame(top_products).sort_values("revenue")
                fig = px.bar(tp_df, x="revenue", y="name", orientation="h", title="Top products by revenue")
                fig.update_traces(marker_color=ACCENT)
                st.plotly_chart(fig, use_container_width=True)

            top_customers = api_get_cached("/reports/top-customers?limit=10")
            if top_customers:
                tc_df = pd.DataFrame(top_customers).sort_values("revenue")
                fig = px.bar(tc_df, x="revenue", y="customer_name", orientation="h", title="Top customers by spend")
                fig.update_traces(marker_color=ACCENT)
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            inv = api_get_cached("/reports/inventory")
            if inv:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total products", f"{inv['total_products']:,}")
                c2.metric("Units in stock", f"{inv['total_units']:,}")
                c3.metric("Low stock", f"{inv['low_stock_count']:,}")
                c4.metric("Inventory value", format_currency(inv["inventory_value"]))

            category_mix = api_get_cached("/reports/category-mix")
            if category_mix:
                folded = top_categories_with_other(category_mix, limit=12)
                cm_df = pd.DataFrame(folded)
                fig = px.pie(cm_df, names="category", values="inventory_value", title="Inventory value by category")
                st.plotly_chart(fig, use_container_width=True)

    elif view == "Notifications":
        st.subheader("\U0001F514 Notifications")
        notifs = api_get_cached("/notifications?audience=admin&limit=50")
        if notifs:
            df = pd.DataFrame(notifs)[["created_at", "message", "level"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No notifications yet.")

    elif view == "Profile Settings":
        st.subheader("\U00002699\U0000FE0F Profile settings")
        u = st.session_state.admin_user
        st.write(f"Email: **{u['email']}**")
        st.write(f"Role: **{u['role']}**")
        with st.form("change_password_form"):
            current = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            if st.form_submit_button("Change password"):
                resp = requests.patch(
                    f"{API_BASE_URL}/users/{u['id']}/password",
                    json={"current_password": current, "new_password": new},
                    timeout=10,
                )
                if resp.status_code == 200:
                    st.success("Password changed")
                else:
                    st.error(resp.json().get("detail", "Could not change password"))
