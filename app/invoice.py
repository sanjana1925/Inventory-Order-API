from fpdf import FPDF

from app.schemas import OrderOut


def build_invoice_pdf(order: OrderOut) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Invoice", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Order #{order.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Customer: {order.customer_name}", new_x="LMARGIN", new_y="NEXT")
    if order.po_reference:
        pdf.cell(0, 8, f"PO reference: {order.po_reference}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Date: {order.created_at:%Y-%m-%d %H:%M}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Status: {order.status.value}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Payment: {order.payment_status.value}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 8, "Product", border=1)
    pdf.cell(20, 8, "Qty", border=1, align="R")
    pdf.cell(35, 8, "Unit price", border=1, align="R")
    pdf.cell(35, 8, "Line total", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    for item in order.items:
        pdf.cell(90, 8, item.product_name[:45], border=1)
        pdf.cell(20, 8, str(item.quantity), border=1, align="R")
        pdf.cell(35, 8, f"R$ {item.unit_price:,.2f}", border=1, align="R")
        pdf.cell(35, 8, f"R$ {item.line_total:,.2f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Subtotal: R$ {order.total:,.2f}", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.cell(0, 7, f"Tax: R$ {order.tax_amount:,.2f}", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.cell(0, 7, f"Shipping: R$ {order.shipping_fee:,.2f}", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Grand total: R$ {order.grand_total:,.2f}", new_x="LMARGIN", new_y="NEXT", align="R")

    return bytes(pdf.output())
