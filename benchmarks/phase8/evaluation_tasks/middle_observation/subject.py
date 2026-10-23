def sample_median(values):
    if not values:
        raise ValueError('empty sample')
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return ordered[middle]
