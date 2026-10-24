def parse_pairs(text):
    result = {}
    for item in text.split(";"):
        parts = item.split("=")
        if len(parts) < 2:
            continue
        key = parts[0].strip()
        value = parts[-1].strip()
        if not key:
            continue
        result[key] = value
    return result
