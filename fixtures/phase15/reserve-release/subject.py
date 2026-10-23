def release_amount(event):
    amount = event.get('amount', 0)
    return amount if type(amount) is int and amount > 0 else 0


def apply_release(state, events):
    held = state['held']
    released = state['released']
    seen = set(state['seen'])
    for event in events:
        if event['id'] in seen:
            continue
        if event.get('status') == 'cancelled':
            continue
        amount = min(held, release_amount(event))
        held -= amount
        released = amount
        seen.add(event['id'])
    return {'held': held, 'released': released, 'seen': sorted(seen)}
