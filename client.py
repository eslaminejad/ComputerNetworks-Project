import socket, threading


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

# connect to webserver
client.connect((host, port))
print("connected to server")


def video_stream(stream_socket):
    cv2.namedWindow('RECEIVING VIDEO')
    cv2.moveWindow('RECEIVING VIDEO', 10, 360)
    fps, st, frames_to_count, cnt = (0, 0, 20, 0)
    while True:
        packet, _ = stream_socket.recvfrom(BUFF_SIZE)
        data = base64.b64decode(packet, ' /')
        npdata = np.fromstring(data, dtype=np.uint8)

        frame = cv2.imdecode(npdata, 1)
        frame = cv2.putText(frame, 'FPS: ' + str(fps), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("RECEIVING VIDEO", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            stream_socket.close()
            print('inja exit')
            os._exit(1)
            break

        if cnt == frames_to_count:
            try:
                fps = round(frames_to_count / (time.time() - st))
                st = time.time()
                cnt = 0
            except:
                print('inja except khord')
                pass
        cnt += 1

    stream_socket.close()
    cv2.destroyAllWindows()


def audio_stream():
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
    # print('server listening at', socket_address)
    client_socket.connect(socket_address)
    # print("CLIENT CONNECTED TO", socket_address)
    data = b""
    payload_size = struct.calcsize("Q")
    while True:
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

        except Exception as e:
            print('except, ajab')
            print(e)
            break

    client_socket.close()
    # os._exit(1)


def get_stream():
    stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    stream_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)

    message = b'Hello'
    stream_socket.sendto(message, (host, stream_port))

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(audio_stream)
        executor.submit(video_stream, stream_socket)


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
