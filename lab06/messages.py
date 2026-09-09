import config

def encode_chat(text, sender):
    return f'CHAT|{sender}|{text}'.encode(config.ENCODING)

def decode_chat(data):
    try:
        parts = data.decode(config.ENCODING).split('|', 2)
        if len(parts) == 3 and parts[0] == 'CHAT':
            return parts[1], parts[2]
    except Exception:
        pass
    return None, None

def encode_beacon(sender):
    return f'BEACON|{sender}'.encode(config.ENCODING)

def decode_beacon(data):
    try:
        parts = data.decode(config.ENCODING).split('|')
        if len(parts) == 2 and parts[0] == 'BEACON':
            return parts[1]
    except Exception:
        pass
    return None

def encode_ignore(ip):
    return f'IGNORE|{ip}'.encode(config.ENCODING)

def decode_ignore(data):
    try:
        parts = data.decode(config.ENCODING).split('|')
        if len(parts) == 2 and parts[0] == 'IGNORE':
            return parts[1]
    except Exception:
        pass
    return None

def encode_leave(sender):
    return f'LEAVE|{sender}'.encode(config.ENCODING)

def decode_leave(data):
    try:
        parts = data.decode(config.ENCODING).split('|')
        if len(parts) == 2 and parts[0] == 'LEAVE':
            return parts[1]
    except Exception:
        pass
    return None
