def stock_delta(row):
    value = row.get("delta", 0)
    return value if type(value) is int else 0


def reconcile_inventory(stock, rows):
    updated = dict(stock)
    for row in rows:
        if row.get("approved") is False:
            continue
        sku = row["sku"]
        updated[sku] = max(0, stock.get(sku, 0) + stock_delta(row))
    return updated
