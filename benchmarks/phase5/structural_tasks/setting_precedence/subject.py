def merge_settings(defaults, overrides):
    """Return a new settings mapping; explicit overrides take precedence."""
    result = overrides.copy()
    result.update(defaults)
    return result
