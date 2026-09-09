import threading
import time
import config
import messages

def receiver(sock, message_queue):
    while True:
        try:
            data, addr = sock.recvfrom(config.BUFFER_SIZE)
            message_queue.put(('net', (data, addr)))
        except OSError:
            break

def start_listener(sock, message_queue):
    t = threading.Thread(target=receiver, args=(sock, message_queue), daemon=True)
    t.start()

def beacon_loop(sock, own_ip, address, stop_event):
    while not stop_event.is_set():
        sock.sendto(messages.encode_beacon(own_ip), address)
        time.sleep(config.BEACON_INTERVAL)

def start_beacon(sock, own_ip, address, stop_event):
    t = threading.Thread(target=beacon_loop, args=(sock, own_ip, address, stop_event), daemon=True)
    t.start()
