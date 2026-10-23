def quote_csv_field(field):
    if ',' in field or '\n' in field:
        return '"' + field.replace('"', '""') + '"'
    return field
