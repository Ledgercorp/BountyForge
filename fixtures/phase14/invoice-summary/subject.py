def item_value(row):
    return row["qty"] * row["unit"]


def invoice_summary(rows, discount_rate, tax_rate):
    if not 0 <= discount_rate <= 1 or not 0 <= tax_rate <= 1:
        raise ValueError("invalid rate")
    active = [row for row in rows if row["state"] != "cancelled"]
    subtotal = sum(item_value(row) for row in active)
    discount = round(subtotal * discount_rate, 2)
    taxable = subtotal
    tax = round(taxable * tax_rate, 2)
    total = round(subtotal + tax, 2)
    return {"subtotal": subtotal, "discount": discount, "tax": tax, "total": total}
