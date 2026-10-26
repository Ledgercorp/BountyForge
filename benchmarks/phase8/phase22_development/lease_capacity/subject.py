def fits(used, units, capacity):
    return used + units <= capacity


def apply_events(state, events, capacity):
    result = dict(state)
    seen = set(state["seen"])
    used = state["used"]
    accepted = 0
    for event in events:
        if event["id"] in seen:
            continue
        units = event["units"]
        if event["kind"] == "acquire" and fits(used, units, capacity):
            used += units
        elif event["kind"] == "release" and used > units:
            used = state["used"] - units
        else:
            continue
        seen.add(event["id"])
        accepted += 1
    result.update(used=used, seen=seen, accepted=accepted)
    return result
