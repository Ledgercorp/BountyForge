def parse_integer_fields(text):
    """Read comma-separated integers, omitting blank fields only."""
    tokens = [part.strip() for part in text.split(',')]
    return [int(token) for token in tokens if token and int(token)]
