#!/usr/bin/env/python3

import socket

udp_ip = "192.168.35.65"
port = 8888
msg = b"hello world"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 8889))

if __name__ == "__main__":
    while True:
        print("sending message...")
        sock.sendto(msg, (udp_ip, port))
        data, addr = sock.recvfrom(1024)
        print(f"received message {data} from {addr}")

