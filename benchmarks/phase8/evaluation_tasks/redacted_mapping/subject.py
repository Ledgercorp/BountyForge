def without_keys(data, keys):
    result = data
    for key in keys:
        result.pop(key, None)
    return result
