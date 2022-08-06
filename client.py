import random
import socket, threading
import sys

import cv2, imutils, socket
import numpy as np
import time, os
import base64
import threading, wave, pyaudio,pickle,struct

BUFF_SIZE = 65536

stream_port = 9688

host = '127.0.0.1'
port = 8550
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

file_port = 8551

global STREAM
STREAM = False

# connect to webserver
client.connect((host, port))
print("connected to server")


def video_stream(stream_socket: socket.socket):
    global STREAM
    winname = 'RECEIVING VIDEO -'+str(random.randint(1000,9999))
    print(winname)
    cv2.namedWindow(winname)
    cv2.moveWindow(winname, 10, 360)
    fps, st, frames_to_count, cnt = (0, 0, 20, 0)
    stream_socket.settimeout(1)
    while True:
        try:
            packet, _ = stream_socket.recvfrom(BUFF_SIZE)
        except:
            break
        data = base64.b64decode(packet, ' /')
        npdata = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(npdata, 1)
        frame = cv2.putText(frame, 'FPS: ' + str(fps), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow(winname, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("video os exit")
            sys.exit()
            stream_socket.close()
            os._exit(1)
            break
        if cnt == frames_to_count:
            try:
                fps = round(frames_to_count / (time.time() - st))
                st = time.time()
                cnt = 0
            except:
                pass
        cnt += 1
    print("video end destroy")
    cv2.destroyWindow(winname)
    stream_socket.close()
    sys.exit()



def audio_stream():
    global STREAM
    p = pyaudio.PyAudio()
    CHUNK = 1024
    stream = p.open(format=p.get_format_from_width(2),
                    channels=2,
                    rate=44100,
                    output=True,
                    frames_per_buffer=CHUNK)

    # create socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_address = (host, stream_port - 1)
    print('server listening at', socket_address)
    client_socket.connect(socket_address)
    print("CLIENT CONNECTED TO", socket_address)
    data = b""
    payload_size = struct.calcsize("Q")
    while STREAM:
        try:
            while len(data) < payload_size:
                packet = client_socket.recv(4 * 1024)  # 4K
                if not packet: break
                data += packet
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]
            while len(data) < msg_size:
                data += client_socket.recv(4 * 1024)
            frame_data = data[:msg_size]
            data = data[msg_size:]
            frame = pickle.loads(frame_data)
            stream.write(frame)

        except:
            break

    print("audio sys exit, STREAM before false: ",STREAM)
    STREAM = False
    sys.exit()
    # client_socket.close()
    # os._exit(1)


def get_stream():
    global STREAM
    STREAM = True
    stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    stream_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)

    message = b'Hello'
    stream_socket.sendto(message, (host, stream_port))

    thread1 = threading.Thread(target=audio_stream, args=([]))
    thread1.start()

    thread2 = threading.Thread(target=video_stream, args=([stream_socket]))
    thread2.start()
    #thread1.join()
    #thread2.join()


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
            elif command == 'stream':
                client.send(message.encode('ascii'))
                # TODO
                get_stream()
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