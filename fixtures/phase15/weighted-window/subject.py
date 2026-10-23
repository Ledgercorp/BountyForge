def row_weight(row):
    weight = row.get('weight', 1)
    return weight if type(weight) in (int, float) and weight > 0 else 0


def summarize_window(rows, start, end):
    numerator = 0
    denominator = 0
    for row in rows:
        if not start <= row['at'] <= end:
            continue
        weight = row_weight(row)
        if row['value'] is None or not weight:
            continue
        numerator += row['value'] * weight
        denominator += 1
    return numerator / denominator if denominator else None
