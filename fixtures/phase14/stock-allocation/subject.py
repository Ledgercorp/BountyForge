def available_units(stock, reserved):
    return max(stock - reserved, 0)


def allocate_orders(stock, reserved, requests):
    available = available_units(stock, reserved)
    allocations = []
    for amount in requests:
        if amount <= 0:
            allocations.append(0)
            continue
        allocated = min(amount, available)
        allocations.append(allocated)
        available = stock - allocated
    return allocations
