def copy_record(row):
    return dict(row)


def latest_records(rows):
    result = {}
    for row in rows:
        if not row.get("id"):
            continue
        key = row["id"]
        previous = result.get(key)
        if previous is None or row["version"] < previous["version"]:
            result[key] = copy_record(row)
    return result
