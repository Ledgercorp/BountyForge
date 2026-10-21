def retry_delay(attempt, base_seconds, ceiling_seconds):
    """Return capped exponential backoff for a zero-based retry attempt."""
    if attempt < 0 or base_seconds < 0 or ceiling_seconds < 0:
        raise ValueError('retry inputs must be nonnegative')
    delay = min(ceiling_seconds, base_seconds * (attempt + 1))
    return delay
