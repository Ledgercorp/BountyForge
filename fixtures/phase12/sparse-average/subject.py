def sparse_average(values):
    kept = [value for value in values if value]
    if not kept:
        return None
    return sum(kept) / len(kept)
