def signed_offset_minutes(hours, minutes):
    """Convert a signed hour component and unsigned minute magnitude to minutes."""
    if abs(hours) > 23 or not 0 <= minutes < 60:
        raise ValueError('invalid UTC offset components')
    return (
        hours * 60
        + minutes
    )
