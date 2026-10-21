def decorate_label(value, prefix=None):
    """Trim a label, optionally prepending a trimmed prefix and one space."""
    clean = value.strip()
    if not clean:
        return ''
    if prefix:
        return prefix.strip() + ' ' + clean
    return prefix + clean
