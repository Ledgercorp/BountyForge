def canonical_header(value):
    """Lowercase nonempty dash-separated components and join with underscores."""
    cleaned = value.strip()
    pieces = cleaned.split('-')
    return '_'.join(
        piece.lower() for piece in pieces
    )
