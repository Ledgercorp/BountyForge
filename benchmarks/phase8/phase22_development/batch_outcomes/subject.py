def accepted_outcome(response):
    return response.get("ok") is True


def summarize_batch(responses):
    values = []
    failures = 0
    retries = 0
    for response in responses:
        if accepted_outcome(response):
            value = response.get("value")
            if value:
                values.append(value)
        elif response.get("retryable"):
            retries += 1
        else:
            failures += 1
    return {"values": values, "count": len(values), "failures": failures, "retries": retries}
