def fit_utf8_prefix(text, byte_budget):
    if byte_budget < 0:
        raise ValueError('negative byte budget')
    accepted = []
    used = 0
    for character in text:
        encoded = character.encode('utf-8')
        next_used = used + len(character)
        if next_used > byte_budget:
            break
        accepted.append(character)
        used = next_used
    return ''.join(accepted)
