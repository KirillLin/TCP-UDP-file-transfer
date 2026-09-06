#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Последовательный сервер для демонстрации работы утилит
Поддерживает команды: ping, traceroute, smurf
"""

import socket
import threading
import sys
import os
import subprocess
import json
import time


class SequentialICMPServer:
    """Последовательный сервер для обработки ICMP команд"""

    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False

    def start(self):
        """Запуск сервера"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
            self.running = True

            print(f"Сервер запущен на {self.host}:{self.port}")
            print("Ожидание подключений...")

            while self.running:
                try:
                    conn, addr = self.sock.accept()
                    print(f"Подключение от {addr[0]}:{addr[1]}")

                    # Последовательная обработка клиента
                    self.handle_client(conn, addr)

                    conn.close()
                    print(f"Отключение от {addr[0]}:{addr[1]}")

                except socket.error as e:
                    if self.running:
                        print(f"Ошибка при приеме подключения: {e}")

        except socket.error as e:
            print(f"Ошибка запуска сервера: {e}")
        finally:
            self.stop()

    def handle_client(self, conn, addr):
        """Обработка одного клиента (последовательно)"""
        try:
            conn.settimeout(30)

            # Отправляем приветствие
            conn.send(b"Welcome to ICMP Server\n")
            conn.send(b"Commands: ping, traceroute, smurf, help, quit\n")
            conn.send(b"> ")

            while True:
                try:
                    data = conn.recv(1024).decode('utf-8').strip()
                    if not data:
                        break

                    if data.lower() == 'quit':
                        conn.send(b"Goodbye!\n")
                        break

                    if data.lower() == 'help':
                        self._send_help(conn)
                        continue

                    # Разбор команды
                    parts = data.split()
                    command = parts[0].lower()

                    if command == 'ping':
                        if len(parts) < 2:
                            conn.send(b"Usage: ping <host1> [host2 ...]\n")
                        else:
                            self._handle_ping(conn, parts[1:])

                    elif command == 'traceroute':
                        if len(parts) < 2:
                            conn.send(b"Usage: traceroute <host>\n")
                        else:
                            self._handle_traceroute(conn, parts[1])

                    elif command == 'smurf':
                        if len(parts) < 3:
                            conn.send(b"Usage: smurf <target_ip> <broadcast_ip> [threads]\n")
                        else:
                            threads = int(parts[3]) if len(parts) > 3 else 10
                            self._handle_smurf(conn, parts[1], parts[2], threads)

                    else:
                        conn.send(f"Unknown command: {command}\n".encode())

                    conn.send(b"> ")

                except socket.timeout:
                    conn.send(b"Timeout. Closing connection.\n")
                    break
                except Exception as e:
                    conn.send(f"Error: {e}\n".encode())
                    break

        except Exception as e:
            print(f"Ошибка обработки клиента {addr}: {e}")

    def _send_help(self, conn):
        """Отправка справки"""
        help_text = """
Available commands:
  ping <host1> [host2 ...]  - Ping one or more hosts
  traceroute <host>          - Trace route to host
  smurf <target> <broadcast> - Smurf attack
  help                       - Show this help
  quit                       - Disconnect
"""
        conn.send(help_text.encode())

    def _handle_ping(self, conn, hosts):
        """Обработка команды ping"""
        try:
            conn.send(f"Pinging {', '.join(hosts)}...\n".encode())

            # Запускаем ping.py как подпроцесс
            cmd = ['sudo', 'python3', 'ping.py', 'ping'] + hosts
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            conn.send(result.stdout.encode())
            if result.stderr:
                conn.send(f"Errors:\n{result.stderr}".encode())

        except subprocess.TimeoutExpired:
            conn.send(b"Ping timeout\n")
        except Exception as e:
            conn.send(f"Error: {e}\n".encode())

    def _handle_traceroute(self, conn, host):
        """Обработка команды traceroute"""
        try:
            conn.send(f"Tracing route to {host}...\n".encode())

            # Запускаем traceroute.py
            cmd = ['sudo', 'python3', 'traceroute.py', host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            conn.send(result.stdout.encode())
            if result.stderr:
                conn.send(f"Errors:\n{result.stderr}".encode())

        except subprocess.TimeoutExpired:
            conn.send(b"Traceroute timeout\n")
        except Exception as e:
            conn.send(f"Error: {e}\n".encode())

    def _handle_smurf(self, conn, target_ip, broadcast_ip, threads):
        """Обработка команды smurf"""
        try:
            conn.send(
                f"Starting Smurf attack: target={target_ip}, broadcast={broadcast_ip}, threads={threads}\n".encode())
            conn.send(b"Attack will run for 10 seconds...\n")

            # Запускаем Smurf атаку с таймаутом
            cmd = ['sudo', 'python3', 'ping.py', 'smurf', target_ip, broadcast_ip, str(threads)]

            # Запускаем в фоновом режиме и убиваем через 10 секунд
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Ждем 10 секунд
            time.sleep(10)
            process.terminate()

            conn.send(b"Attack completed (10 seconds)\n")

        except Exception as e:
            conn.send(f"Error: {e}\n".encode())

    def stop(self):
        """Остановка сервера"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        print("Сервер остановлен")


def print_usage():
    """Вывод справки"""
    print("Использование:")
    print("  sudo python3 server.py [host] [port]")
    print()
    print("Примеры:")
    print("  sudo python3 server.py")
    print("  sudo python3 server.py 192.168.1.10 8888")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help', 'help'):
        print_usage()
        sys.exit(0)

    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

    server = SequentialICMPServer(host, port)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == "__main__":
    main()