import socket, threading

host = '127.0.0.1'
port = 8550
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

file_port = 8551

# connect to webserver
client.connect((host, port))
print("connected to server")

def echo():
    while True:
        try:
            #message = input("enter your message:\n")
            message = input()
            command = message.split()[0]
            if command == 'upload':
                filename = message.split()[2]
                client.send(('upload ' + message.split()[1]).encode('ascii'))
                file_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                file_client.connect((host, file_port))
                with file_client, open(filename, 'rb') as file:
                    sendfile = file.read()
                    file_client.sendall(sendfile)
                print('file sent')
            else:
                client.send(message.encode('ascii'))
        except IOError as e:
            print(e)
            print("io error")
        except socket.error:
            print("socket error")
            client.close()
            break


def read():
    while True:
        try:
            message = client.recv(1024).decode('ascii')
            print(message)
        except:
            print("err read")
            client.close()
            break


echo_thread = threading.Thread(target=echo)
echo_thread.start()

read_thread = threading.Thread(target=read)
read_thread.start()
