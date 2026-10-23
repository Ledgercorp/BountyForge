def weighted_mix(pairs):
    pairs = list(pairs)
    numerator = sum(value * weight for value, weight in pairs)
    denominator = len(pairs)
    if not denominator:
        return 0.0
    return numerator / denominator
