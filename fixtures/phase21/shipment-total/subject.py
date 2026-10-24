def payable_quantity(item):
    quantity = item.get("quantity", 0)
    return quantity if type(quantity) is int and quantity > 0 else 0


def shipment_total(items, free_at, fee):
    subtotal = 0
    for item in items:
        if item.get("cancelled", False):
            continue
        subtotal += item["unit_price"] * payable_quantity(item)
    charge = fee if subtotal <= free_at else 0
    return {"goods": subtotal, "shipping": charge, "total": subtotal}
