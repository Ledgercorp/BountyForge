def summarize_numbers(numbers):
    """Return the count and arithmetic total, including for an empty list."""
    if numbers:
        count = len(numbers)
        total = sum(numbers)
    else:
        count = 0
    return {'count': count, 'total': total}
