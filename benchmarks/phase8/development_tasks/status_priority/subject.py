def classify_status(status, attempts, retry_limit):
    """Only transient failures consume the bounded retry allowance."""
    if attempts < 0 or retry_limit < 0:
        raise ValueError('Retry counts must be nonnegative')
    if status == 'ok':
        return 'complete'
    if (
        attempts >= retry_limit
    ):
        return 'held'
    if status in ('busy', 'transient'):
        return 'retry'
    return 'rejected'
