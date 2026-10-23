def decode_network_word(data):
    if not isinstance(data, bytes) or len(data) != 2:
        raise ValueError('two bytes required')
    return data[0] | (data[1] << 8)
