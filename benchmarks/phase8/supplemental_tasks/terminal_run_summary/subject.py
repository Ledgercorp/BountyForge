def summarize_runs(events):
    runs = []
    if not events:
        return runs
    current = events[0]
    count = 0
    for event in events:
        if event == current:
            count += 1
        else:
            runs.append((current, count))
            current = event
            count = 1
    return runs
