#!/usr/bin/env/python3

import socket
import time

udp_ip = "192.168.96.65"
port = 8888
msg = b"hello world"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind(("0.0.0.0", 8889))
# sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

if __name__ == "__main__":
    while True:
        time.sleep(0.1)
        print("sending message...")
        sock.sendto(msg, (udp_ip, port))
        # data, addr = sock.recvfrom(1024)
        # print(f"received message {data} from {addr}")

