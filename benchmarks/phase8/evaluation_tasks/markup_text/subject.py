def escape_markup(text):
    return (
        text.replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('&', '&amp;')
    )
