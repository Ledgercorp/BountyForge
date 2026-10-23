def transpose_cells(rows):
    if not rows:
        return []
    width = len(rows[0])
    if any(len(row) > width for row in rows):
        raise ValueError('ragged rows')
    return [list(column) for column in zip(*rows)]
