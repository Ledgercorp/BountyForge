def first_values(pairs):
    """Build a dictionary keeping the first value for each repeated key."""
    result = {}
    for key, value in pairs:
        if key in result:
            result[key] = value
    return result
