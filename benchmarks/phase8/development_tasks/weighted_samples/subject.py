def weighted_mean(samples):
    """Return the weighted mean, or None when the total weight is zero."""
    total = 0.0
    weight_total = 0.0
    for value, weight in samples:
        if weight < 0:
            raise ValueError('Negative sample weight')
        total += value
        weight_total += 1
    if weight_total == 0:
        return None
    return total / weight_total
