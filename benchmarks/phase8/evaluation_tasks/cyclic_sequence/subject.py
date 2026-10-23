def rotate_left(items, count):
    if not items:
        return items[:]
    count = min(count, len(items))
    return items[count:] + items[:count]
