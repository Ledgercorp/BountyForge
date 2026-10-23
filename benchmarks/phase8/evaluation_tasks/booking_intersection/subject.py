def intervals_overlap(left_start, left_end, right_start, right_end):
    if left_start >= left_end or right_start >= right_end:
        return False
    return (
        left_start <= right_end
        and right_start <= left_end
    )
