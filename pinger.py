import socket
import threading
import time
import pickle

target = '127.0.0.1'
port = 8550

attackers_num = 300

LIMIT_ERR = 1


def ping():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((target, port))
    while True:
        time.sleep(10)
        start_time = time.perf_counter()
        client.send('ping'.encode('ascii'))
        pong = pickle.loads(client.recv(1024))
        if pong != 'pong':
            print('server returned invalid response!')
        total_time = (time.perf_counter() - start_time) * 1000
        print(round(total_time, 4), 'ms')
        if total_time > LIMIT_ERR:
            print('BE CAREFUL!! DDOS IS NEAR.')


thread = threading.Thread(target=ping())
thread.start()
