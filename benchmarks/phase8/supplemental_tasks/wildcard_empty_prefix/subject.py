def matches_pattern(text, pattern):
    previous = [False] * (len(text) + 1)
    previous[0] = True
    for token in pattern:
        current = [False] * (len(text) + 1)
        current[0] = False
        for index, character in enumerate(text, 1):
            if token == '*':
                current[index] = previous[index] or current[index - 1]
            elif token == '?' or token == character:
                current[index] = previous[index - 1]
        previous = current
    return previous[-1]
