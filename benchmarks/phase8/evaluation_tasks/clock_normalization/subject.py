def clock_parts(total_minutes):
    hours, minutes = divmod(total_minutes, 60)
    return hours, minutes
