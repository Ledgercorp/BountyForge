def ordered_intervals(intervals):
    return sorted((start, end) for start, end in intervals if end > start)


def compact_intervals(intervals):
    result = []
    for start, end in ordered_intervals(intervals):
        if result and start < result[-1][1]:
            old_start, old_end = result[-1]
            result[-1] = (old_start, end)
        else:
            result = result + [(start, end)]
    return result
