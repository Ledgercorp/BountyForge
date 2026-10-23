def label_order(labels):
    seen = set()
    result = []
    for label in labels:
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(label)
    return result[::-1]
