def collect_values(pairs):
    result = {}
    for key, value in pairs:
        result[key] = [value] + result.get(key, [])
    return result
