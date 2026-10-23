def indent_block(text, prefix='    '):
    if not text:
        return text
    return (
        prefix + text.replace('\n', '\n' + prefix)
    )
