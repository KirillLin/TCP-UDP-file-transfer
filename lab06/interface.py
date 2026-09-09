import socket
import psutil

UNUSABLE_PREFIXES = {'lo', 'lo0', 'docker', 'veth', 'vmnet', 'vboxnet', 'utun', 'tun', 'tap', 'ppp', 'vpn', 'wg'}

def _is_unusable(name):
    lowered = name.lower()
    return any(
        lowered == p or lowered.startswith(p)
        for p in UNUSABLE_PREFIXES
    )

def _find_ipv4(addr_list):
    for a in addr_list:
        if a.family != socket.AF_INET or a.address.startswith('127.'):
            continue
        if a.netmask == '255.255.255.255':
            continue
        return a
    return None

def _to_int(ip):
    parts = [int(x) for x in ip.split('.')]
    return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]

def _to_ip(value):
    return '.'.join(str((value >> i) & 0xff) for i in (24, 16, 8, 0))

def _broadcast(ip, netmask):
    return _to_ip(_to_int(ip) | (~_to_int(netmask) & 0xffffffff))

def _get_routed_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()

def _make_info(name, addrs, stats):
    if name not in stats or not stats[name].isup or _is_unusable(name):
        return None
    inet = _find_ipv4(addrs)
    if not inet:
        return None
    bcast = inet.broadcast
    if not bcast and inet.netmask:
        bcast = _broadcast(inet.address, inet.netmask)
    if not bcast:
        bcast = '255.255.255.255'
    return name, inet.address, inet.netmask, bcast

def get_interface_info():
    routed = _get_routed_ip()
    stats = psutil.net_if_stats()
    all_addrs = psutil.net_if_addrs()
    if routed:
        for name, addrs in all_addrs.items():
            inet = _find_ipv4(addrs)
            if inet and inet.address == routed:
                info = _make_info(name, addrs, stats)
                if info:
                    return info
    for name, addrs in all_addrs.items():
        info = _make_info(name, addrs, stats)
        if info:
            return info
    raise RuntimeError('No active IPv4 interface found')
