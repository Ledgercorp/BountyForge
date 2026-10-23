def inclusive_window(values, lower, upper):
    selected = [value for value in values if lower <= value < upper]
    return selected
