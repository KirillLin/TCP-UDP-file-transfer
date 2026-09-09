import argparse
import queue
import threading
import config
import interface
import messages
import network
import peers
import sockets

def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=('broadcast', 'multicast'), default='broadcast')
    return p

def get_destination(mode, broadcast):
    if mode == 'broadcast':
        return (broadcast, config.BCAST_PORT)
    return (config.MCAST_GROUP, config.MCAST_PORT)

def get_socket(mode, ip):
    if mode == 'broadcast':
        return sockets.make_broadcast_socket(config.BCAST_PORT)
    return sockets.make_multicast_socket(config.MCAST_GROUP, config.MCAST_PORT, ip)

def show_interface(name, ip, mask, broadcast):
    print(f'interface {name}')
    print(f'ip {ip}')
    print(f'mask {mask}')
    print(f'broadcast {broadcast}')

def show_help():
    print()
    print('commands: /list, /ignore <ip>, /leave, /help, /quit')

def read_input(message_queue):
    while True:
        try:
            line = input()
            message_queue.put(('input', line))
        except EOFError:
            message_queue.put(('input', None))
            break

def handle_chat(sock, line, own_ip, address, peer_state):
    if line is None:
        return 'quit'
    line = line.strip()
    if not line:
        return
    if line[0] != '/':
        sock.sendto(messages.encode_chat(line, own_ip), address)
        return
    if line == '/list':
        active = peer_state.list_all()
        if not active:
            print(f'\r\nno peers', flush=True)
        else:
            print(flush=True)
            for ip in active:
                print(ip, flush=True)
        return
    if line == '/help':
        show_help()
        return
    if line == '/quit':
        return 'quit'
    if line.startswith('/ignore '):
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            print(f'\r\nusage: /ignore <ip>', flush=True)
            return
        target = parts[1]
        peer_state.ignore(target)
        print(f'\r\nignoring {target}', flush=True)
        sock.sendto(messages.encode_ignore(target), address)
        return
    if line == '/leave':
        sock.sendto(messages.encode_leave(own_ip), address)
        return 'leave'
    print(f'\r\nunknown command', flush=True)

def process_packet(data, addr, own_ip, peer_state):
    ip = addr[0]
    if ip == own_ip or ip == '127.0.0.1':
        return
    target = messages.decode_ignore(data)
    if target:
        peer_state.ignore(target)
        print(f'\r\n{ip} ignores {target}', flush=True)
        return
    leaver = messages.decode_leave(data)
    if leaver:
        peer_state.forget(leaver)
        print(f'\r\n{leaver} left', flush=True)
        return
    sender = messages.decode_beacon(data)
    if sender:
        if peer_state.touch(sender):
            print(f'\r\npeer {sender}', flush=True)
        return
    sender, text = messages.decode_chat(data)
    if not sender:
        return
    peer_state.touch(sender)
    if not peer_state.is_ignored(sender):
        print(f'\r\n{sender}: {text}', flush=True)

def run_loop(sock, mode, own_ip, address, peer_state, message_queue, stop):
    while True:
        kind, payload = message_queue.get()
        if kind == 'input':
            result = handle_chat(sock, payload, own_ip, address, peer_state)
            if result == 'quit':
                break
            if result == 'leave':
                if mode == 'multicast':
                    sockets.drop_multicast(sock, config.MCAST_GROUP, own_ip)
                    print(f'\r\nleft multicast group', flush=True)
                else:
                    print(f'\r\nleft', flush=True)
                stop.set()
        elif kind == 'net':
            process_packet(payload[0], payload[1], own_ip, peer_state)

def main():
    args = build_parser().parse_args()
    name, ip, mask, broadcast = interface.get_interface_info()
    show_interface(name, ip, mask, broadcast)
    mode = args.mode
    address = get_destination(mode, broadcast)
    print(f'mode {mode}')
    show_help()
    sock = get_socket(mode, ip)
    peer_state_obj = peers.Peers(config.PEER_TIMEOUT)
    message_queue = queue.Queue()
    stop = threading.Event()
    network.start_listener(sock, message_queue)
    network.start_beacon(sock, ip, address, stop)
    input_thread = threading.Thread(target=read_input, args=(message_queue,), daemon=True)
    input_thread.start()
    try:
        run_loop(sock, mode, ip, address, peer_state_obj, message_queue, stop)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        sock.close()

if __name__ == '__main__':
    main()
