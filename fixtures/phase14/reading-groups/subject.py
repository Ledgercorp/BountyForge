def sensor_key(name):
    return name.strip().casefold()


def group_readings(records):
    groups = {}
    for name, value in records:
        key = sensor_key(name)
        groups.setdefault(key, []).append(value)
    result = {}
    for key, raw in groups.items():
        valid = [value for value in raw if value]
        result[key] = sum(valid) / len(raw) if valid else None
    return result
