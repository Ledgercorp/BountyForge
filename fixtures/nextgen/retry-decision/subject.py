def transient(status):
    return status in (408, 429) or 500 <= status < 600


def retry_decision(status, attempt, limit, base_delay, cap):
    if transient(status):
        if attempt > limit:
            return {'retry': False, 'attempt': attempt, 'delay': 0}
        delay = min(cap, base_delay + attempt)
        return {'retry': True, 'attempt': attempt + 1, 'delay': delay}
    return {'retry': False, 'attempt': attempt, 'delay': 0}
