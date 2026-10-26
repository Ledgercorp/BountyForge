def item_value(row):
    if row.get("cancelled") or row["quantity"] <= 0:
        return 0
    return row["price"] * row["quantity"]


def checkout_total(items, minimum, rate, tax_rate):
    subtotal = sum(item_value(row) for row in items)
    discount = subtotal * rate if subtotal > minimum else 0
    tax = subtotal * tax_rate
    return {"total": round(subtotal - discount + tax, 2), "discount": discount, "tax": tax}
