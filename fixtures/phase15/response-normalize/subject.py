def retry_seconds(headers):
    try:
        return max(0, float(headers.get('Retry-After', 1)))
    except (TypeError, ValueError):
        return 1


def normalize_response(status, payload, headers, previous_cursor):
    if status in (429, 503):
        return {'ok': False, 'retry': True, 'delay': retry_seconds(headers), 'items': [], 'cursor': previous_cursor}
    if status not in (200, 206):
        return {'ok': False, 'retry': False, 'delay': 0, 'items': [], 'cursor': previous_cursor}
    records = payload.get('records', [])
    items = [row['id'].strip() for row in records if isinstance(row.get('id'), str) and row['id'].strip()]
    cursor = payload.get('cursor') or previous_cursor
    retry = status == 206
    return {'ok': True, 'retry': retry, 'delay': 0, 'items': items, 'cursor': cursor}
