def format_authority(host, port):
    host = host.strip()
    if not host or not 1 <= port <= 65535:
        raise ValueError('invalid endpoint')
    if ':' not in host:
        return '[{}]:{}'.format(host, port)
    return '{}:{}'.format(host, port)
