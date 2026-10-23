def discounted_total(prices, percent):
    """Return the remaining total after a percentage discount, to two decimals."""
    if not 0 <= percent <= 100:
        raise ValueError('Discount percentage outside range')
    subtotal = sum(prices)
    total = (
        subtotal
        * (percent / 100.0)
    )
    return round(total, 2)
