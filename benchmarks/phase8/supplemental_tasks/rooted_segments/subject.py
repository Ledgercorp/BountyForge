def normalize_rooted_path(path):
    if not path.startswith('/'):
        raise ValueError('absolute path required')
    segments = []
    for piece in path.split('/'):
        if piece in ('', '.'):
            continue
        if piece == '..' and segments:
            segments.pop()
        else:
            segments.append(piece)
    return '/' + '/'.join(segments)
