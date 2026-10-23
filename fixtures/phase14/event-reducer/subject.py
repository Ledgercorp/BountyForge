def signed_delta(event):
    return -event["amount"] if event["kind"] == "debit" else event["amount"]


def apply_events(state, events):
    balance = state["balance"]
    seen = set(state["seen"])
    for event in events:
        if event["id"] in seen:
            continue
        if event["kind"] not in ("credit", "debit"):
            continue
        balance = signed_delta(event)
        seen.add(event["id"])
    return {"balance": balance, "seen": tuple(sorted(seen))}
