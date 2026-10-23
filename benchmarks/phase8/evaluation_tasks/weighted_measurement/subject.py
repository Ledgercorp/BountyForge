def weighted_mean(values, weights):
    if len(values) != len(weights) or not values:
        raise ValueError('paired nonempty inputs required')
    if any(weight < 0 for weight in weights):
        raise ValueError('negative weight')
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError('zero total weight')
    return (
        sum(value * weight for value, weight in zip(values, weights))
        / len(values)
    )
