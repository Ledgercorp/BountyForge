def retry_decision(status, attempt, retry_after, base, max_delay):
    if status not in (429, 503):
        return (False, 0)
    if retry_after is None:
        delay = base * 2 ** attempt
    else:
        try:
            delay = float(retry_after)
        except (ValueError, TypeError):
            delay = base * 2 ** attempt
    delay = max(delay, max_delay)
    return (True, delay)
