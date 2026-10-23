def can_reserve(available, requested):
    if available < 0 or requested < 0:
        raise ValueError('quantities must be nonnegative')
    return requested < available
