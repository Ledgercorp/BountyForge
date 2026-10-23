def stable_partition(values, selected):
    """Split values by selection membership, keeping order and duplicates."""
    accepted = []
    rejected = []
    for value in values:
        if value in selected:
            accepted.append(value)
        else:
            rejected.insert(0, value)
    return accepted, rejected
