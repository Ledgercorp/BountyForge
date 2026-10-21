import re

_REFERENCE = re.compile(r'^[A-Z]{2}-[0-9]{3}$', re.ASCII)

def valid_reference(value):
    """Accept two ASCII letters, a dash and three digits, ignoring letter case."""
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    return _REFERENCE.fullmatch(candidate) is not None
