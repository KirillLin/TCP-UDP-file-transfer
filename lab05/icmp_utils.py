#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Общие утилиты для работы с ICMP протоколом
"""

import socket
import struct
import time


def calculate_checksum(data):
    """
    Расчет контрольной суммы для ICMP пакета
    Алгоритм из RFC 1071
    """
    if len(data) % 2 != 0:
        data += b'\x00'

    sum_val = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        sum_val += word

    sum_val = (sum_val >> 16) + (sum_val & 0xFFFF)
    sum_val += (sum_val >> 16)
    return ~sum_val & 0xFFFF


def create_icmp_request(icmp_id, icmp_seq, timestamp):
    """
    Создание ICMP Echo Request пакета с временной меткой в теле
    """
    icmp_type = 8
    icmp_code = 0
    checksum_val = 0

    # Заголовок ICMP
    header = struct.pack('bbHHh', icmp_type, icmp_code, checksum_val, icmp_id, icmp_seq)
    # Данные: временная метка (8 байт)
    data = struct.pack('d', timestamp)
    packet = header + data

    # Расчет контрольной суммы
    checksum_val = calculate_checksum(packet)
    header = struct.pack('bbHHh', icmp_type, icmp_code, socket.htons(checksum_val), icmp_id, icmp_seq)

    return header + data


def parse_icmp_response(packet, expected_id):
    """
    Парсинг ICMP ответа
    Возвращает: (type, code, src_ip, rtt, is_ours)
    """
    if len(packet) < 28:
        return None, None, None, None, False

    # Извлекаем IP-заголовок
    ip_header = packet[:20]
    src_ip = socket.inet_ntoa(ip_header[12:16])

    # Извлекаем ICMP-заголовок
    icmp_offset = 20
    if len(packet) < icmp_offset + 8:
        return None, None, None, None, False

    icmp_type, icmp_code = struct.unpack('bb', packet[icmp_offset:icmp_offset + 2])

    # Обработка Echo Reply (Type 0)
    if icmp_type == 0:
        p_id = struct.unpack('H', packet[icmp_offset + 4:icmp_offset + 6])[0]
        if p_id != expected_id:
            return None, None, None, None, False

        # Извлекаем временную метку
        timestamp_offset = icmp_offset + 8
        if len(packet) >= timestamp_offset + 8:
            sent_time = struct.unpack('d', packet[timestamp_offset:timestamp_offset + 8])[0]
            rtt = (time.time() - sent_time) * 1000  # в миллисекундах
            return icmp_type, icmp_code, src_ip, rtt, True
        return icmp_type, icmp_code, src_ip, None, True

    # Обработка Time Exceeded (Type 11) и Destination Unreachable (Type 3)
    elif icmp_type in (11, 3):
        # В теле ответа содержится оригинальный IP + ICMP пакет
        inner_offset = icmp_offset + 8  # пропускаем ICMP заголовок ответа

        if len(packet) < inner_offset + 20 + 8:
            return None, None, None, None, False

        # Пропускаем внутренний IP-заголовок (20 байт)
        inner_ip_offset = inner_offset + 20

        if len(packet) < inner_ip_offset + 8:
            return None, None, None, None, False

        # Извлекаем ID из вложенного ICMP
        inner_id = struct.unpack('H', packet[inner_ip_offset + 4:inner_ip_offset + 6])[0]

        if inner_id != expected_id:
            return None, None, None, None, False

        # Извлекаем временную метку из вложенного пакета
        timestamp_offset = inner_ip_offset + 8
        if len(packet) >= timestamp_offset + 8:
            sent_time = struct.unpack('d', packet[timestamp_offset:timestamp_offset + 8])[0]
            rtt = (time.time() - sent_time) * 1000
            return icmp_type, icmp_code, src_ip, rtt, True

        return icmp_type, icmp_code, src_ip, None, True

    return None, None, None, None, False


def create_ip_header(source_ip, dest_ip, proto=1, ttl=64):
    """
    Создание IP-заголовка для Smurf-атаки
    """
    ip_ihl = 5
    ip_ver = 4
    ip_tos = 0
    ip_tot_len = 20 + 28  # IP заголовок + ICMP пакет
    ip_id = 54321
    ip_frag_off = 0
    ip_ttl = ttl
    ip_proto = proto
    ip_check = 0

    ip_ihl_ver = (ip_ver << 4) + ip_ihl

    ip_header = struct.pack('!BBHHHBBH4s4s',
                            ip_ihl_ver, ip_tos, ip_tot_len,
                            ip_id, ip_frag_off,
                            ip_ttl, ip_proto, ip_check,
                            socket.inet_aton(source_ip),
                            socket.inet_aton(dest_ip))

    # Расчет контрольной суммы IP
    ip_check = calculate_checksum(ip_header)
    ip_header = struct.pack('!BBHHHBBH4s4s',
                            ip_ihl_ver, ip_tos, ip_tot_len,
                            ip_id, ip_frag_off,
                            ip_ttl, ip_proto, socket.htons(ip_check),
                            socket.inet_aton(source_ip),
                            socket.inet_aton(dest_ip))

    return ip_header


def get_icmp_type_message(icmp_type, icmp_code):
    """
    Возвращает текстовое описание для типа ICMP
    """
    if icmp_type == 0:
        return "Echo Reply"
    elif icmp_type == 3:
        messages = {
            0: "Network Unreachable",
            1: "Host Unreachable",
            2: "Protocol Unreachable",
            3: "Port Unreachable",
            4: "Fragmentation Needed",
            5: "Source Route Failed",
            6: "Destination Network Unknown",
            7: "Destination Host Unknown",
            9: "Network Prohibited",
            10: "Host Prohibited",
            13: "Admin Prohibited"
        }
        return messages.get(icmp_code, f"Destination Unreachable (code {icmp_code})")
    elif icmp_type == 8:
        return "Echo Request"
    elif icmp_type == 11:
        if icmp_code == 0:
            return "TTL Expired"
        else:
            return "Time Exceeded"
    else:
        return f"Type {icmp_type}, Code {icmp_code}"