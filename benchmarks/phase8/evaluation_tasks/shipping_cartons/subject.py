def carton_count(items, capacity):
    if items < 0 or capacity <= 0:
        raise ValueError('invalid quantity or capacity')
    count = (
        items // capacity
    )
    return count
