import socket
import threading

import cv2, imutils, socket
import numpy as np
import time
import base64
import threading, wave, pyaudio,pickle,struct
import sys
import queue
import os

BUFF_SIZE = 65536


host = '127.0.0.1'
port = 8550
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen(1)
file_port = 8551
file_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
file_server.bind((host, file_port))
file_server.listen(2)
print("server listening")

users = {'ali': '123'}

stream_port = 9688
stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
stream_socket.bind((host, stream_port))

class User:
    username = ''
    password = ''
    logged_in = False

    def register(self, inputusername, inputpassword):
        if inputusername not in users:
            self.username = inputusername
            self.password = inputpassword
            self.logged_in = True
            users[inputusername] = inputpassword
            return True
        else:
            return False

    def login(self, inputusername, inputpassword):
        if inputusername in users:
            if users[inputusername] == inputpassword:
                self.username = inputusername
                self.pasword = inputpassword
                self.logged_in = True
                return True
        else:
            return False

    def logout(self):
        if self.logged_in:
            self.logged_in = False
            return True
        else:
            return False


class Video():
    owner: str
    likes: list
    dislikes: list
    comments: list
    title: str

    def __init__(self, owner, title):
        self.owner = owner
        self.title = title
        self.likes = []
        self.dislikes = []
        self.comments = []

    def upload(self):
        soc, addr = file_server.accept()
        print(f'client connect to upload file {addr}')
        savefilename = 'data/' + self.title
        with soc, open(savefilename, 'wb') as file:
            recvfile = soc.recv(4096)
            while True:
                file.write(recvfile)
                recvfile = soc.recv(4096)
                if not recvfile:
                    break
        print("File has been received.")


def handle_user(message, user):
    if message.split()[0] == 'register' and len(message.split()) == 3:
        inputusername = message.split()[1]
        inputpassword = message.split()[2]
        register = user.register(inputusername, inputpassword)
        if register == True:
            return 'register successful'
        else:
            return 'register error'

    elif message.split()[0] == 'login' and len(message.split()) == 3:
        inputusername = message.split()[1]
        inputpassword = message.split()[2]
        login = user.login(inputusername, inputpassword)
        if login == True:
            return 'login successful'
        else:
            return 'login error'

    elif message.split()[0] == 'logout' and len(message.split()) == 1:
        logout = user.logout()
        if logout == True:
            return 'logout successful'
        else:
            return 'logout error'


def handle(client: socket.socket):
    user = User()
    while True:
        try:
            message = client.recv(1024).decode('ascii')
            print(message)
            if message.split()[0] in ['login', 'logout', 'register']:
                result = handle_user(message, user, )
                client.send(result.encode('ascii'))

            elif message.split()[0] == 'upload':
                if user.logged_in:
                    title = message.split()[1]
                    video = Video(user.username, title)
                    video.upload()
                else:
                    client.send('you need to login'.encode('ascii'))
            elif message.split()[0] == 'stream':
                if user.logged_in:
                    client.send('be prepare'.encode('ascii'))
                    filename = 'data/' + message.split()[1]
                    stream_video(filename)
                else:
                    client.send('you need to login'.encode('ascii'))

        except Exception as e:
            print(e)
            print("err sv handle")
            client.close()
            break


def video_stream_gen(vid, q):
    WIDTH = 400
    while (vid.isOpened()):
        try:
            _, frame = vid.read()
            frame = imutils.resize(frame, width=WIDTH)
            q.put(frame)
        except:
            os._exit(1)
    print('Player closed')
    BREAK = True
    vid.release()


def video_stream(q, FPS):
    global TS
    fps, st, frames_to_count, cnt = (0, 0, 1, 0)
    cv2.namedWindow('TRANSMITTING VIDEO')
    cv2.moveWindow('TRANSMITTING VIDEO', 10, 30)
    while True:
        msg, client_addr = stream_socket.recvfrom(BUFF_SIZE)
        print('GOT connection from ', client_addr)
        WIDTH = 400

        while (True):
            frame = q.get()
            encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            message = base64.b64encode(buffer)
            stream_socket.sendto(message, client_addr)
            frame = cv2.putText(frame, 'FPS: ' + str(round(fps, 1)), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 0, 255), 2)
            if cnt == frames_to_count:
                try:
                    fps = (frames_to_count / (time.time() - st))
                    st = time.time()
                    cnt = 0
                    if fps > FPS:
                        TS += 0.001
                    elif fps < FPS:
                        TS -= 0.001
                    else:
                        pass
                except:
                    pass
            cnt += 1

            cv2.imshow('TRANSMITTING VIDEO', frame)
            key = cv2.waitKey(int(1000 * TS)) & 0xFF
            if key == ord('q'):
                os._exit(1)
                TS = False
                break


def audio_stream(filename):
    s = socket.socket()
    s.bind((host, (stream_port - 1)))

    s.listen(5)
    CHUNK = 1024
    command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {}".format(filename, 'data/temp.wav')
    os.system(command)
    wf = wave.open("temp.wav", 'rb')
    p = pyaudio.PyAudio()
    print('server listening at', (host, (stream_port - 1)))
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    input=True,
                    frames_per_buffer=CHUNK)

    client_socket, addr = s.accept()

    while True:
        if client_socket:
            while True:
                data = wf.readframes(CHUNK)
                a = pickle.dumps(data)
                message = struct.pack("Q", len(a)) + a
                client_socket.sendall(message)


def stream_video(filename):
    q = queue.Queue(maxsize=10)
    vid = cv2.VideoCapture(filename)
    FPS = vid.get(cv2.CAP_PROP_FPS)
    global TS
    TS = (0.5 / FPS)
    BREAK = False
    print('FPS:', FPS, TS)
    totalNoFrames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    durationInSeconds = float(totalNoFrames) / float(FPS)
    d = vid.get(cv2.CAP_PROP_POS_MSEC)
    print(durationInSeconds, d)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.submit(audio_stream, filename)
        executor.submit(video_stream_gen, vid, q)
        executor.submit(video_stream, q, FPS)

while True:
    client, address = server.accept()

    print(f"client connected with {address}")

    client.send("connected".encode('ascii'))

    thread = threading.Thread(target=handle, args=([client]))
    thread.start()
