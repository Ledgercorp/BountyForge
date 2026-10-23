def describe_seconds(seconds):
    if seconds < 0:
        raise ValueError('negative duration')
    unit = 'second' if seconds <= 1 else 'seconds'
    return '{} {}'.format(seconds, unit)
