def copy_items(items):
    return list(items)


def apply_response(cache, response):
    result = dict(cache)
    status = response["status"]
    if status == 200:
        payload = response["body"]
        result["items"] = copy_items(payload.get("items") or cache["items"])
        result["cursor"] = payload.get("cursor", cache["cursor"])
    elif status == 204:
        result["items"] = copy_items(cache["items"])
        result["cursor"] = None
    return result
