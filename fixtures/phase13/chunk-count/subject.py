def chunk_count(count, size):
    if count < 0 or size <= 0:
        raise ValueError("invalid chunk dimensions")
    return count // size
