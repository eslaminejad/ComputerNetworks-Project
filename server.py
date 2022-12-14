import atexit
import base64
import os
import pickle
import queue
import random
import socket
import struct
import sys
import threading
import time
import wave

import cv2
import imutils
import pyaudio

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

users = {'ali': ['123', 'normal', 0, -1], 'manager': ['supreme_manager#2022', 'manager', 0, -1]}
# 3rd item is total number of uploaded video. 4th is index of last video deleted.
waiting_admins = []
videos = []
strike_users = []
tickets = []

global STREAM
STREAM = False

stream_port = 9688
stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
stream_socket.bind((host, stream_port))

login_not_need = ['register', 'login', 'stream', 'video_list', 'video_detail', 'command_list', 'quit', 'ping']
valid_commands = {'normal': ['logout', 'stream', 'video_list', 'video_detail', 'upload', 'like',
                             'comment', 'command_list', 'ping', 'add_ticket', 'ticket_details', 'my_tickets', 'quit'],
                  'admin': ['logout', 'add_tag', 'video_list', 'video_detail', 'stream', 'delete_video',
                            'fix_strike', 'get_strike_users', 'command_list', 'ping', 'add_ticket', 'ticket_details',
                            'my_tickets', 'get_tickets', 'change_ticket_status', 'add_ticket_response', 'quit'],
                  'manager': ['logout', 'approve_admin', 'get_requests', 'command_list', 'ping', 'ticket_details',
                              'get_tickets', 'change_ticket_status', 'add_ticket_response', 'quit']}

usual_commands = ['register [username] [password] [optional:admin]', 'login [username] [password]',
                  'stream [name].[format]', 'video_list', 'video_detail [name].[format]', 'command_list', 'ping',
                  'quit']
special_commands = {'normal': ['logout', 'upload [name].[format] [local address]', 'like [like/dis] [name].[format]',
                               'comment [name].[format] [comment]'],
                    'admin': ['logout', 'add_tag [name].[format] [tag]', 'delete_video [name].[format]',
                              'fix_strike [username]', 'get_strike_users',
                              'change_ticket [id] [new/in_progress/done]'],
                    'manager': ['logout', 'approve_admin [username]', 'get_requests']}


class User:
    username = ''
    password = ''
    logged_in = False
    type = ''
    uploaded_video_num = 0
    last_video_deleted = -1

    def register(self, input_username, input_password):
        if input_username not in users:
            self.username = input_username
            self.password = input_password
            self.logged_in = True
            self.type = 'normal'
            users[input_username] = [input_password, 'normal', 0, -1]
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
                self.uploaded_video_num = users[input_username][2]
                self.last_video_deleted = users[input_username][3]
                return True
            return False
        else:
            return False

    def logout(self):
        if self.logged_in:
            self.logged_in = False
            self.type = ''
            return True
        else:
            return False


class Ticket:
    class Status:
        New = 'new'
        InProgress = 'in_progress'
        Done = 'done'
        Closed = 'closed'

    StatusList = [Status.New, Status.InProgress, Status.Done, Status.Closed]

    def __init__(self, owner, text, type):
        self.type = type
        self.owner = owner
        self.text = text
        self.id = random.randint(10 ** 3, 10 ** 4)
        self.status = self.Status.New
        self.response = None

    def represent(self):
        return dict(
            id=self.id,
            status=self.status,
            owner=self.owner,
            text=self.text,
            response=self.response
        )


class Video:
    title: str
    owner: str
    likes: list
    dislikes: list
    comments: list
    risk_tags: list
    owner_index: int

    def __init__(self, owner, title, owner_index):
        self.owner = owner
        self.title = title
        self.likes = []
        self.dislikes = []
        self.comments = []
        self.risk_tags = []
        self.owner_index = owner_index

    def upload(self):
        soc, adder = file_server.accept()
        print(f'client connect to upload file {adder}')
        saveasfilename = 'data/' + self.title
        iter = 0
        with soc, open(saveasfilename, 'wb') as file:
            received = soc.recv(4096)
            while iter < 12800:
                file.write(received)
                received = soc.recv(4096)
                if not received:
                    break
                iter += 1
        if iter == 12800:
            return 'file size is too large.'
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


def get_video_by_title(t):
    for vid in videos:
        if vid.title == t:
            return vid
    return None


def like_dis_video(like_not, title, username):
    video = get_video_by_title(title)
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
    video = get_video_by_title(title)
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
    users[username] = [info[0], 'admin', info[2], info[3]]
    return username + ' approved as admin.'


def add_risk_tag(video_title, tag):
    vid = get_video_by_title(video_title)
    if not vid:
        return 'video is not found.'
    vid.risk_tags.append(tag)
    return 'tag added.'


def get_valid_commands(user):
    commands = usual_commands
    if user.type != '':
        commands.pop(0)
        commands.pop(0)
        commands += special_commands[user.type]
    return commands


def get_video_detail(title):
    vid = get_video_by_title(title)
    if vid is None:
        return 'invalid video title!'
    else:
        detail = {'owner': vid.owner,
                  'likes': len(vid.likes),
                  'dislikes': len(vid.dislikes),
                  'comments': vid.comments,
                  'restriction': vid.risk_tags}
        return detail


def delete_video(title):
    vid = get_video_by_title(title)
    if vid is None:
        return 'there is not video with this name.'
    videos.remove(vid)
    if os.path.exists('data/' + title):
        os.remove('data/' + title)
    new_deleted = vid.owner_index
    use = users[vid.owner]
    if abs(new_deleted - use[3]) == 1:
        strike_users.append(vid.owner)
        use[3] = -1
        message = 'user added to strike list.'
    else:
        use[3] = new_deleted
        message = 'video deleted.'
    users[vid.owner] = use
    return message


def fix_strike(username):
    if username not in strike_users:
        return 'this user is not in strike list'
    strike_users.remove(username)
    return 'successful'


def add_ticket(user, text):
    tickets.append(Ticket(owner=user.username, text=text, type=user.type))
    return 'ticket added successfully'


def get_my_tickets(user):
    return [ticket.represent() for ticket in filter(lambda x: x.owner == user.username, tickets)]


def get_tickets(user):
    expected_type = 'normal' if user.type == 'admin' else 'admin'
    return [(ticket.id, ticket.status) for ticket in filter(lambda x: x.type == expected_type, tickets)]


def get_ticket_details(id):
    for ticket in tickets:
        if ticket.id == id:
            return ticket.represent()
    return 'ticket not found'


def add_response(id, text):
    found_ticket = None
    for ticket in tickets:
        if ticket.id == id:
            found_ticket = ticket
    if not found_ticket:
        return 'ticket not found'
    if found_ticket.status == Ticket.Status.Closed:
        return 'this ticket has been closed'
    found_ticket.response = text
    return 'ticket response added successfully'


def change_ticket_status(id, status):
    if status not in Ticket.StatusList:
        return 'not a valid status'
    for ticket in tickets:
        if ticket.id == id:
            ticket.status = status
    return 'ticket status changed successfully'


global last_req
last_req = {}
REQ_GAP = 0.5


def handle(client: socket.socket, addr, ISPROXY: bool):
    # TODO
    # ADMIN SHOULD have 'ISPORXY'==TRUE  to access commands
    user = User()
    while True:
        try:
            message = client.recv(1024).decode('ascii')
            # print(addr)

            # Handling DDOS
            global last_req
            if addr not in last_req:
                last_req[addr] = time.perf_counter()
            else:
                new_req = time.perf_counter()
                if new_req - last_req[addr] < REQ_GAP:
                    client.close()
                    break
                last_req[addr] = new_req

            print(message)
            split_message = message.split()
            command = split_message[0]
            if (command not in login_not_need) and (not user.logged_in):
                client.send(pickle.dumps('you need to login'))
            elif user.logged_in and (command not in valid_commands[user.type]):
                client.send(pickle.dumps('this command is not valid for you.'))
            elif command in ['login', 'logout', 'register']:
                result = pickle.dumps(handle_user(command, split_message, user))
                client.send(result)
            elif user.type == 'admin' and not ISPROXY:
                client.send(pickle.dumps('Connect to Proxy first!'))
            elif command == 'upload':
                title = split_message[1]
                if get_video_by_title(title):
                    client.send(pickle.dumps('video title is invalid.'))
                elif user.username in strike_users:
                    client.send(pickle.dumps('user is in strike list and can not upload video.'))
                else:
                    client.send(pickle.dumps('successful'))
                    video = Video(user.username, title, user.uploaded_video_num + 1)
                    result = video.upload()
                    if result == 'successful':
                        videos.append(video)
                        user.uploaded_video_num += 1
                        users[user.username] = [user.password, user.type, user.uploaded_video_num,
                                                user.last_video_deleted]
                    else:
                        if os.path.exists('data/' + title):
                            os.remove('data/' + title)
                    client.send(pickle.dumps(result))
            elif command == 'stream':
                if get_video_by_title(split_message[1]):
                    client.send(pickle.dumps('successful'))
                    filename = 'data/' + split_message[1]
                    thread2 = threading.Thread(target=stream_video, args=([filename]))
                    print(thread2.name, "def start stream")
                    thread2.start()
                    # thread2.join()
                    # stream_video(filename)
                    print("AFTER STREAM")
                else:
                    client.send(pickle.dumps('there is not video by this name.'))

            elif command == 'video_list':
                result = pickle.dumps(get_video_list())
                client.send(result)
            elif command == 'like':
                result = pickle.dumps(like_dis_video(split_message[1], split_message[2], user.username))
                client.send(result)
            elif command == 'comment':
                com = ' '.join(split_message[2:])
                result = pickle.dumps(comment_video(split_message[1], com, user.username))
                client.send(result)
            elif command == 'get_requests':
                result = pickle.dumps(waiting_admins)
                client.send(result)
            elif command == 'get_strike_users':
                result = pickle.dumps(strike_users)
                client.send(result)

            elif command == 'approve_admin':
                result = pickle.dumps(approve_admin(split_message[1]))
                client.send(result)
            elif command == 'add_tag':
                tag = ' '.join(split_message[2:])
                result = pickle.dumps(add_risk_tag(split_message[1], tag))
                client.send(result)
            elif command == 'command_list':
                result = pickle.dumps(get_valid_commands(user))
                client.send(result)
            elif command == 'video_detail':
                result = pickle.dumps(get_video_detail(split_message[1]))
                client.send(result)
            elif command == 'delete_video':
                result = pickle.dumps(delete_video(split_message[1]))
                client.send(result)
            elif command == 'fix_strike':
                result = pickle.dumps(fix_strike(split_message[1]))
                client.send(result)
            elif command == 'quit':
                raise socket.error
            elif command == 'ping':
                client.send(pickle.dumps('pong'))
            elif command == 'add_ticket':
                result = add_ticket(user, ' '.join(split_message[1:]))
                client.send(pickle.dumps(result))
            elif command == 'ticket_details':
                result = get_ticket_details(int(split_message[1]))
                client.send(pickle.dumps(result))
            elif command == 'my_tickets':
                result = get_my_tickets(user)
                client.send(pickle.dumps(result))
            elif command == 'get_tickets':
                result = get_tickets(user)
                client.send(pickle.dumps(result))
            elif command == 'change_ticket_status':
                result = change_ticket_status(int(split_message[1]), split_message[2])
                client.send(pickle.dumps(result))
            elif command == 'add_ticket_response':
                result = add_response(int(split_message[1]), ' '.join(split_message[2:]))
                client.send(pickle.dumps(result))
            else:
                client.send(pickle.dumps('invalid command! enter command_list for help.'))

        except socket.error as e:
            print(e)
            print("err sv handle")
            with open("users.pkl", "wb") as fp:
                pickle.dump(users, fp)
            with open("strike_users.pkl", "wb") as fp:
                pickle.dump(strike_users, fp)
            with open("waiting_admins.pkl", "wb") as fp:
                pickle.dump(waiting_admins, fp)
            with open("videos.dat", "wb") as f:
                pickle.dump(videos, f)
            with open("tickets.dat", "wb") as f:
                pickle.dump(tickets, f)
            client.close()
            break
        except Exception as e:
            print(e)
            client.send(pickle.dumps('invalid command! enter command_list for help.'))


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
            print(threading.currentThread().name, "*")
            break
            # os._exit(1)
    print('Player closed,stream before false: ', STREAM)
    BREAK = True
    vid.release()
    STREAM = False

    sys.exit()


def video_stream(q, FPS):
    global TS
    global STREAM
    fps, st, frames_to_count, cnt = (0, 0, 1, 0)
    # cv2.namedWindow('TRANSMITTING VIDEO')
    # cv2.moveWindow('TRANSMITTING VIDEO', 10, 30)
    while True:
        msg, client_addr = stream_socket.recvfrom(BUFF_SIZE)
        print('GOT connection from ', client_addr)
        WIDTH = 400

        while True:

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

            # cv2.imshow('TRANSMITTING VIDEO', frame)
            key = cv2.waitKey(int(1000 * TS)) & 0xFF
            if key == ord('q'):
                print("video os exit")
                for thread in threading.enumerate():
                    print(thread.name)
                os._exit(1)

                TS = False
                break
    print("after video stream")
    cv2.destroyWindow('TRANSMITTING VIDEO')
    sys.exit()


def audio_stream(filename: str):
    s = socket.socket()
    s.bind((host, (stream_port - 1)))

    s.listen(5)
    CHUNK = 1024
    print("line 220")
    if os.path.exists(filename.split('.')[0] + '.wav'):
        os.remove(filename.split('.')[0] + '.wav')
    command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {}".format(filename, filename.split('.')[0] + '.wav')
    os.system(command)
    print("line 227")
    wf = wave.open(filename.split('.')[0] + '.wav', 'rb')
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
    print("after audio", STREAM)
    if os.path.exists(filename.split('.')[0] + '.wav'):
        os.remove(filename.split('.')[0] + '.wav')


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
    print(thread3.name, "audio_stream")
    thread3.start()

    thread4 = threading.Thread(target=video_stream_gen, args=([vid, q]))
    print(thread4.name, "video_stream_gen")
    thread4.start()

    thread5 = threading.Thread(target=video_stream, args=([q, FPS]))
    print(thread5.name, "video_stream")
    thread5.start()


try:
    with open("users.pkl", "rb") as fp:
        users = pickle.load(fp)
    with open("strike_users.pkl", "rb") as fp:
        strike_users = pickle.load(fp)
    with open("waiting_admins.pkl", "rb") as fp:
        waiting_admins = pickle.load(fp)
    with open("videos.dat", 'rb') as fp:
        videos = pickle.load(fp)
    with open("tickets.dat", 'rb') as f:
        tickets = pickle.load(f)
except:
    print('error in load data')

client = None


def exit_handler():
    with open("users.pkl", "wb") as fp:
        pickle.dump(users, fp)
    with open("strike_users.pkl", "wb") as fp:
        pickle.dump(strike_users, fp)
    with open("waiting_admins.pkl", "wb") as fp:
        pickle.dump(waiting_admins, fp)
    with open("videos.dat", "wb") as f:
        pickle.dump(videos, f)
    with open("tickets.dat", "wb") as f:
        pickle.dump(tickets, f)
    if client:
        client.close()


atexit.register(exit_handler)

while True:
    client, address = server.accept()

    print(f"client connected with {address}")
    message = client.recv(1024).decode('ascii')
    print(message)
    ISPROXY = False
    if message == 'proxy':
        ISPROXY = True
    client.send(pickle.dumps("connected"))

    threadstart = threading.Thread(target=handle, args=([client, str(address[0]) + ':' + str(address[1]), ISPROXY]))
    # print(threadstart.name,"thread start connection")
    threadstart.start()
