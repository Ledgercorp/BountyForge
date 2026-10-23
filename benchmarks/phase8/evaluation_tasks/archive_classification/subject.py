def archive_suffix(name):
    suffixes = (
        '.gz', '.tar.gz', '.zip'
    )
    lowered = name.lower()
    for suffix in suffixes:
        if lowered.endswith(suffix):
            return suffix
    return ''
