def page_rows(response):
    return response.get("items", [])


def ingest_page(response, previous_cursor):
    status = response.get("status", 500)
    if status == 429:
        return {"rows": [], "cursor": previous_cursor, "complete": False, "retry": True}
    if status != 200:
        return {"rows": [], "cursor": previous_cursor, "complete": False, "retry": False}
    rows = page_rows(response)
    cursor = response.get("next_cursor") or previous_cursor
    complete = bool(cursor)
    return {"rows": rows, "cursor": cursor, "complete": complete, "retry": False}
