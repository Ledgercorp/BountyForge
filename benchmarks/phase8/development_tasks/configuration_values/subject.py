def parse_configuration(lines):
    """Read colon-delimited settings; values may themselves contain colons."""
    values = {}
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith('#'):
            continue
        parts = raw.split(':')
        key, value = parts
        values[key.strip()] = value.strip()
    return values
