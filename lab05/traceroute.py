#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита traceroute с поддержкой:
- Определения пути до узла назначения
- Обработки TTL expired, Echo Reply, Destination Unreachable
- Временных меток в теле пакета
- Использования MSG_PEEK
"""

import os
import socket
import sys
import time
from icmp_utils import (
    create_icmp_request,
    parse_icmp_response,
    get_icmp_type_message
)


def traceroute_hop(host, ttl, icmp_id, timeout=2):
    """
    Выполнение одного hop'а traceroute
    Возвращает: (icmp_type, icmp_code, src_ip, rtt, error)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        sock.settimeout(timeout)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)

        # Отправляем запрос с временной меткой
        timestamp = time.time()
        packet = create_icmp_request(icmp_id, ttl, timestamp)
        sock.sendto(packet, (host, 1))

        # Получаем ответ с MSG_PEEK
        while True:
            try:
                # Заглядываем в буфер без удаления
                peek_packet, peek_addr = sock.recvfrom(1024, socket.MSG_PEEK)

                # Парсим пакет
                icmp_type, icmp_code, src_ip, rtt, is_ours = parse_icmp_response(peek_packet, icmp_id)

                if is_ours:
                    # Наш пакет - удаляем из буфера
                    sock.recvfrom(1024)
                    sock.close()
                    return icmp_type, icmp_code, src_ip, rtt, None
                else:
                    # Не наш пакет - удаляем из буфера
                    sock.recvfrom(1024)

            except socket.timeout:
                sock.close()
                return None, None, None, None, "Timeout"

    except PermissionError:
        return None, None, None, None, "Permission denied (need sudo)"
    except socket.error as e:
        return None, None, None, None, f"Socket error: {e}"
    except Exception as e:
        return None, None, None, None, f"Error: {e}"


def print_hop(ttl, icmp_type, icmp_code, src_ip, rtt, error):
    """
    Вывод информации о hop'е
    """
    if error:
        print(f"{ttl:2d}  *  {error}")
        return

    if icmp_type is None:
        print(f"{ttl:2d}  *  No response")

    elif icmp_type == 0:
        # Echo Reply - достигли цели
        rtt_str = f"{rtt:.2f}ms" if rtt is not None else "N/A"
        print(f"{ttl:2d}  {src_ip:15s}  {rtt_str}  [REACHED]")

    elif icmp_type == 11:
        # Time Exceeded
        rtt_str = f"{rtt:.2f}ms" if rtt is not None else "N/A"
        msg = "TTL expired" if icmp_code == 0 else "Time exceeded"
        print(f"{ttl:2d}  {src_ip:15s}  {rtt_str}  [{msg}]")

    elif icmp_type == 3:
        # Destination Unreachable
        rtt_str = f"{rtt:.2f}ms" if rtt is not None else "N/A"
        msg = get_icmp_type_message(icmp_type, icmp_code)
        print(f"{ttl:2d}  {src_ip:15s}  {rtt_str}  [{msg}]")

    else:
        rtt_str = f"{rtt:.2f}ms" if rtt is not None else "N/A"
        msg = get_icmp_type_message(icmp_type, icmp_code)
        print(f"{ttl:2d}  {src_ip:15s}  {rtt_str}  [{msg}]")


def traceroute(host, max_hops=30, timeout=2):
    """
    Трассировка маршрута до хоста
    """
    print(f"Трассировка маршрута до {host}")
    print(f"Максимальное количество прыжков: {max_hops}")
    print("-" * 70)
    print("TTL  IP адрес           Время    Статус")
    print("-" * 70)

    icmp_id = os.getpid() & 0xFFFF
    reached = False
    unreachable = False

    for ttl in range(1, max_hops + 1):
        icmp_type, icmp_code, src_ip, rtt, error = traceroute_hop(host, ttl, icmp_id, timeout)

        print_hop(ttl, icmp_type, icmp_code, src_ip, rtt, error)

        # Если достигли цели или хост недостижим - завершаем
        if icmp_type == 0:
            reached = True
            break
        if icmp_type == 3:
            unreachable = True
            break

    print("-" * 70)

    if reached:
        print(f"Маршрут до {host} найден")
    elif unreachable:
        print(f"Хост {host} недостижим")
    else:
        print(f"Маршрут не найден (превышено количество прыжков)")


def print_usage():
    """Вывод справки"""
    print("Использование:")
    print("  sudo python3 traceroute.py <host> [max_hops] [timeout]")
    print()
    print("Примеры:")
    print("  sudo python3 traceroute.py 8.8.8.8")
    print("  sudo python3 traceroute.py google.com 20 3")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    host = sys.argv[1]
    max_hops = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 2

    traceroute(host, max_hops, timeout)


if __name__ == "__main__":
    main()