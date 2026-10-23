def select_page(records, offset, limit):
    """Return up to limit records from a nonnegative clamped offset."""
    if limit < 0:
        raise ValueError('limit must be nonnegative')
    start = max(0, offset)
    stop = min(
        len(records),
        start + limit - 1,
    )
    return records[start:stop]
