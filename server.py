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
import enum

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

users = {'ali': ['123', 'normal'], 'manager': ['supreme_manager#2022', 'manager']}
waiting_admins = []
videos = []


global STREAM
STREAM = False

stream_port = 9688
stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
stream_socket.bind((host, stream_port))

login_not_need = ['register', 'login', 'stream', 'video_list']
valid_commands = {'normal': ['logout', 'stream', 'upload', 'like', ' comment'],
                  'admin': ['Add_tag', 'stream', 'delete_video', 'fix_strike'],
                  'manager': ['approve_admin', 'get_requests']}
## should implement get comment and likes and ...


class User:
    username = ''
    password = ''
    logged_in = False
    type = 'normal'

    def register(self, input_username, input_password):
        if input_username not in users:
            self.username = input_username
            self.password = input_password
            self.logged_in = True
            users[input_username] = [input_password, 'normal']
            return True
        else:
            return False

    def login(self, input_username, input_password):
        if input_username in users:
            if users[input_username][0] == input_password:
                self.username = input_username
                self.password = input_password
                self.logged_in = True
                self.type = users[input_username][1]
                return True
            return False
        else:
            return False

    def logout(self):
        if self.logged_in:
            self.logged_in = False
            return True
        else:
            return False


class Video():
    title: str
    owner: str
    likes: list
    dislikes: list
    comments: list
    risk_tags: list

    def __init__(self, owner, title):
        self.owner = owner
        self.title = title
        self.likes = []
        self.dislikes = []
        self.comments = []
        self.risk_tags = []

    def upload(self):
        soc, adder = file_server.accept()
        print(f'client connect to upload file {adder}')
        saveasfilename = 'data/' + self.title
        with soc, open(saveasfilename, 'wb') as file:
            received = soc.recv(4096)
            while True:
                file.write(received)
                received = soc.recv(4096)
                if not received:
                    break
        print("File has been received.")
        return 'successful'


def handle_user(command, split_message, user):
    if command == 'register':
        if len(split_message) == 3:
            input_username = split_message[1]
            input_password = split_message[2]
            register = user.register(input_username, input_password)
            if register:
                return 'register successful'
            else:
                return 'register error'
        elif len(split_message) == 4 and split_message[3] == 'admin':
            input_username = split_message[1]
            input_password = split_message[2]
            register = user.register(input_username, input_password)
            if register:
                waiting_admins.append(input_username)
                return 'register successful. waiting to approve by manager.'
            else:
                return 'register error'
    elif command == 'login' and len(split_message) == 3:
        input_username = split_message[1]
        input_password = split_message[2]
        login = user.login(input_username, input_password)
        if login:
            return 'login successful'
        else:
            return 'login error'

    elif command == 'logout':
        logout = user.logout()
        if logout:
            return 'logout successful'
        else:
            return 'logout error'

    return 'invalid command'


def find_video_by_title(t):
    for vid in videos:
        if vid.title == t:
            return vid
    return None


def like_dis_video(like_not, title, username):
    video = find_video_by_title(title)
    if not video:
        return 'there is not video by this name.'
    if like_not == 'like':
        if username in video.likes:
            video.likes.remove(username)
            return 'you previously like this video. your like has been removed'
        if username in video.dislikes:
            video.dislikes.remove(username)
        video.likes.append(username)
    else:
        if username in video.dislikes:
            video.dislikes.remove(username)
            return 'you previously dislike this video. your dislike has been removed'
        if username in video.likes:
            video.likes.remove(username)
        video.dislikes.append(username)
    return 'your ' + like_not + ' has been approved.'


def comment_video(title, comment, username):
    video = find_video_by_title(title)
    if not video:
        return 'there is not video by this name.'
    video.comments.append([username, comment])
    return 'comment added successfully.'


def get_video_list():
    title_list = []
    for vid in videos:
        title_list.append(vid.title)
    return title_list


def approve_admin(username):
    if username not in waiting_admins:
        return 'username is not valid.'
    info = users[username]
    waiting_admins.remove(username)
    users[username] = [info[0], 'admin']
    return username + ' approved as admin.'


def add_risk_tag(video_title, tag):
    vid = find_video_by_title(video_title)
    if not vid:
        return 'video is not found.'
    vid.risk_tags.append(tag)
    return 'tag added.'


def handle(client: socket.socket):
    user = User()
    while True:
        try:
            message = client.recv(1024).decode('ascii')
            split_message = message.split()
            command = split_message[0]
            if (command not in login_not_need) and (not user.logged_in):
                client.send('you need to login'.encode('ascii'))
            elif user.logged_in and (command not in valid_commands[user.type]):
                client.send('this command is not valid for you.'.encode('ascii'))
            elif command in ['login', 'logout', 'register']:
                result = handle_user(command, split_message, user)
                client.send(result.encode('ascii'))
            elif command == 'upload':
                title = split_message[1]
                video = Video(user.username, title)
                videos.append(video)
                result = video.upload()
                client.send(result.encode('ascii'))
            elif command == 'stream':
                client.send('be prepare'.encode('ascii'))
                filename = 'data/' + split_message[1]
                thread2 = threading.Thread(target=stream_video, args=([filename]))
                print(thread2.name,"def start stream")
                thread2.start()
                #thread2.join()
                # stream_video(filename)
                print("AFTER STREAM")

            elif command == 'video_list':
                print("AFTER STREAM")
                result = get_video_list()
                client.send(result.encode('ascii'))
            elif command == 'like':
                result = like_dis_video(split_message[1], split_message[2], user.username)
                client.send(result.encode('ascii'))
            elif command == 'comment':
                result = comment_video(split_message[1], split_message[2], user.username)
                client.send(result.encode('ascii'))
            elif command == 'get_requests':
                result = waiting_admins
                client.send(result.encode('ascii'))
            elif command == 'approve_admin':
                result = approve_admin(split_message[1])
                client.send(result.encode('ascii'))
            elif command == 'Add_tag':
                result = add_risk_tag(split_message[1], split_message[2])
                client.send(result.encode('ascii'))


        except Exception as e:
            print(e)
            print("err sv handle")
            np.save('users.npy', users)
            np.save('waiting_admins.npy', waiting_admins)
            with open("videos.dat", "wb") as f:
                pickle.dump(videos, f)
            client.close()
            break


def video_stream_gen(vid, q):
    global STREAM
    WIDTH = 400
    while (vid.isOpened()):
        try:
            _, frame = vid.read()
            frame = imutils.resize(frame, width=WIDTH)
            q.put(frame)
        except:
            print("except video gen")
            for thread in threading.enumerate():
                print(thread.name)
            print(threading.currentThread().name,"*")
            break
            # os._exit(1)
    print('Player closed,stream before false: ',STREAM)
    BREAK = True
    vid.release()
    STREAM = False

    sys.exit()



def video_stream(q, FPS):
    global TS
    global STREAM
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
                print("video os exit")
                for thread in threading.enumerate():
                    print(thread.name)
                os._exit(1)

                TS = False
                break
    print("after video stream")

    sys.exit()


def audio_stream(filename):
    s = socket.socket()
    s.bind((host, (stream_port - 1)))

    s.listen(5)
    CHUNK = 1024
    print("line 220")
    if os.path.exists('data/temp.wav'):
        os.remove('data/temp.wav')
    command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {}".format(filename, 'data/temp.wav')
    os.system(command)
    print("line 227")
    wf = wave.open("data/temp.wav", 'rb')
    p = pyaudio.PyAudio()
    print('server listening at', (host, (stream_port - 1)))
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    input=True,
                    frames_per_buffer=CHUNK)

    client_socket, addr = s.accept()

    while STREAM:
        if client_socket:
            while STREAM:
                data = wf.readframes(CHUNK)
                a = pickle.dumps(data)
                message = struct.pack("Q", len(a)) + a
                client_socket.sendall(message)
    print("after audio",STREAM)

def stream_video(filename):
    global STREAM
    STREAM = True
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

    thread3 = threading.Thread(target=audio_stream, args=([filename]))
    print(thread3.name,"audio_stream")
    thread3.start()

    thread4 = threading.Thread(target=video_stream_gen, args=([vid, q]))
    print(thread4.name,"video_stream_gen")
    thread4.start()

    thread5 = threading.Thread(target=video_stream, args=([q, FPS]))
    print(thread5.name,"video_stream")
    thread5.start()


while True:
    try:
        users = np.load('users.npy', allow_pickle=True).item()
        waiting_admins = np.load('waiting_admins.npy')
        with open("videos.dat") as f:
            videos = pickle.load(f)
    except:
        print('error in load data')

    client, address = server.accept()

    print(f"client connected with {address}")

    client.send("connected".encode('ascii'))

    threadstart = threading.Thread(target=handle, args=([client]))
    print(threadstart.name,"thread start connection")
    threadstart.start()