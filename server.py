import random
import socket, threading

host = '127.0.0.1'
port = 8550
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen(1)
print("server listening")

users = {'ali':'123'}

class User():
    username = ''
    password = ''
    logged_in = False

    def register(self,inputusername, inputpassword):
        if inputusername not in users:
            self.username = inputusername
            self.password = inputpassword
            self.logged_in = True
            users[inputusername] = inputpassword
            return True
        else:
            return False

    def login(self,inputusername, inputpassword):
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
    owner : str
    likes : list
    dislikes : list
    comments : list
    title : str

    def __init__(self, owner, title):
        self.owner = owner
        self.title = title
        self.likes = []
        self.dislikes = []
        self.comments = []

    def upload(self, soc):
        savefilename = 'data/'+self.title+'.mp4'
        with soc, open(savefilename, 'wb') as file:
            while True:
                recvfile = soc.recv(4096)
                print(recvfile)
                if not recvfile: break
                file.write(recvfile)
        print("File has been received.")

def handle_user(message,user):
    if message.split()[0] == 'register' and len(message.split()) == 3:
        inputusername = message.split()[1]
        inputpassword = message.split()[2]
        register = user.register(inputusername,inputpassword)
        if register == True:
            return 'register successful'
        else:
            return 'register error'

    elif message.split()[0] == 'login' and len(message.split()) == 3:
        inputusername = message.split()[1]
        inputpassword = message.split()[2]
        login = user.login(inputusername,inputpassword)
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
            if message.split()[0] in ['login','logout','register']:
                result = handle_user(message,user, )
                client.send(result.encode('ascii'))

            elif message.split()[0] == 'upload':
                if user.logged_in :
                    title = message.split()[1]
                    video = Video(user.username, title)
                    video.upload(client)
                else:
                    client.send('you need to login'.encode('ascii'))

        except Exception as e:
            print(e)
            print("err sv handle")
            client.close()
            break



while True:
    client, address = server.accept()

    print(f"client connected with {address}")

    client.send("connected".encode('ascii'))

    thread = threading.Thread(target=handle, args=([client]))
    thread.start()
