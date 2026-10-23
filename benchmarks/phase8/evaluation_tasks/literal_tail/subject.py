def remove_suffix(text, suffix):
    if not suffix or not text.endswith(suffix):
        return text
    return text.replace(suffix, '')
