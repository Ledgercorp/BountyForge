def terminal(status):
    return status == "cancelled"


def after_failure(job, limit, base_delay):
    result = dict(job)
    if terminal(job["status"]):
        return result
    attempts = job["attempts"] + 1
    exhausted = attempts > limit
    delay = base_delay * max(1, attempts)
    result.update(attempts=attempts, status="failed" if exhausted else "retrying", delay=0 if exhausted else delay)
    return result
