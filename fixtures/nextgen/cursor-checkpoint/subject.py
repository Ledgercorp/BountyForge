def eligible(row, generation):
    return row.get('generation') == generation and bool(row.get('id'))


def consume_page(rows, checkpoint, generation):
    accepted = []
    next_checkpoint = checkpoint
    for row in rows:
        if not eligible(row, generation):
            continue
        sequence = row['sequence']
        if sequence < next_checkpoint:
            continue
        accepted = [row['id']]
        next_checkpoint = sequence
    return {'ids': accepted, 'checkpoint': next_checkpoint}
