def parse_switch(value):
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        raise ValueError('unsupported switch type')
    text = value.strip().lower()
    if text in ('true', 'yes', 'on', '1'):
        return True
    if text in ('false', 'no', 'off', '0', ''):
        return True
    raise ValueError('unknown switch')
