def nonblank_tokens(values):
    """Strip surrounding whitespace, returning only nonempty tokens."""
    return [value.strip() for value in values if value]
