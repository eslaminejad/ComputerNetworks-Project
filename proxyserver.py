import pickle
import socket
import struct
import threading
import random

host = '127.0.0.1'
port = 7777

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen(1)
print("proxy-server listening")


global iptable
iptable = {}

def clienttoserver(client:socket.socket, server:socket.socket):
    while True:
        message = client.recv(1024)
        print('client : ',message.decode('ascii'))
        server.send(message)

def servertoclient(client: socket.socket, server: socket.socket):
    while True:
        message = server.recv(1024)
        print('server : ',pickle.loads(message))
        client.send(message)

def handle(client : socket.socket, ipaddress, port):
    host = '127.0.0.1'
    port = 8550
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    global iptable
    #generate random ip
    iptable[ipaddress] = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
    print(iptable[ipaddress])
    # connect to proxyserver
    server.connect((host, port))
    message = pickle.loads(server.recv(1024))
    print(message)
    print("connected")

    thread1 = threading.Thread(target=clienttoserver, args=([client, server]))
    thread1.start()

    thread2 = threading.Thread(target=servertoclient, args=([client, server]))
    thread2.start()


while True:
    client, address = server.accept()

    print(f"client connected with {address}")

    client.send('connected'.encode('ascii'))

    threadstart = threading.Thread(target=handle, args=([client, str(address[0]),str(address[1])]))
    # print(threadstart.name,"thread start connection")
    threadstart.start()
