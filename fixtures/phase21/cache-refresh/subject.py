def response_value(response):
    return response.get("value")


def refresh_cache(cache, response):
    result = dict(cache)
    if response["status"] == 200:
        result["value"] = response_value(response)
        result["etag"] = response.get("etag", cache.get("etag"))
        result["attempts"] = 0
    elif response["status"] == 304:
        result["value"] = None
        result["attempts"] = 0
    else:
        result["attempts"] = 1
    return result
