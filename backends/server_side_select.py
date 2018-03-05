# -*- coding: utf-8 -*-
import socket
import select
from . import server_side


class ServerSideSelect(server_side.ChatServer):

    def __init__(self,port=5247):
        server_side.ChatServer.__init__(self)
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind(('', port))
        self.serverSocket.listen(5)
        self.serverSocket.setblocking(False)
        self.CONNECTION_LIST.append(self.serverSocket)

        self.id_to_socket = {}  # socket session字典 id : socket
        self.socket_to_id = {}  # socket session 字典 socket:id
        print("server wait for connect....")


    def auth(self,password):
        if password == self.PASSWORD:
            return 0
        else:
            return 1#0登录成功1登录失败

    def login(self,login_data,sock):#新用户登录
        try:
            login_data = login_data.decode('utf-8')
            id = login_data.split('||')[0]
            password = login_data.split('||')[1]
        except IndexError as e:
            print(login_data)
            print(e)
        else:
            auth_result = self.auth(password)
            if auth_result == 0:
                print("%s login"%id)
                self.id_to_socket[id] = sock
                self.socket_to_id[sock] = id
                sock.send('hello %s,you login successed'%id)
                self.CONNECTION_LIST.append(sock)#要在这里把socket加进来才行
            else:
                sock.send("Password inncorrect")

    def chat(self,sock):#点对点聊天，发送消息格式id||信息
        try:
            data = sock.recv(self.inBufSize)
            data = data.decode('utf-8')
        except Exception:
            print("sender is offline")
            sock.close()
        else:
            if data == '':
                sender_id = self.socket_to_id[sock]
                print("%s is offline"%sender_id)
                self.CONNECTION_LIST.remove(sock)
                sock.close()
                return 0
            try:
                remote_id = data.split('||')[0]
                message = data.split('||')[1]
            except IndexError as e:
                print(data)
                print(e)
            else:
                print("id = %s,message = %s"%(remote_id,message))
                local_id = self.socket_to_id[sock]
                self.pre_send(local_id, message, remote_id)

    def pre_send(self, local_id, message, remote_id):
        if remote_id == 'all':
            self.broadcast(local_id, message)
        else:
            self.p2psend(local_id, message, remote_id)

    def p2psend(self,local_id,message,remote_id):
        try:
            remote_socket = self.id_to_socket[remote_id]
        except KeyError:
            local_socket = self.id_to_socket[local_id]
            local_socket.send("remote %s is offline"%remote_id)
        else:
            message_send = "%s said : %s" % (local_id, message)
            message_send = message_send.encode('utf-8')
            try:
                remote_socket.sendall(message_send)
            except Exception as e:
                print(e)
                remote_socket.close()
                self.CONNECTION_LIST.remove(remote_socket)

    def broadcast(self,local_id,message):
        for sock in self.CONNECTION_LIST:
            if sock == self.serverSocket:
                continue
            else:
                try:
                    message_send = "%s said : %s" % (local_id, message)
                    sock.send(message_send)
                except Exception as e:
                    print(e)
                    sock.close()
                    self.CONNECTION_LIST.remove(sock)
                    continue

    def socet_handle(self):
        # Get the list sockets which are ready to be read through select
        while 1:
            try:
                read_sockets, write_sockets, error_sockets = select.select(self.CONNECTION_LIST, [], [])
            except:
                continue
            for sock in read_sockets:
                # New connection
                if sock == self.serverSocket:  # 用户通过主socket（即服务器开始创建的 socket，一直处于监听状态）来登录
                    # Handle the case in which there is a new connection recieved through server_socket
                    sockfd, addr = self.serverSocket.accept()
                    login_data = sockfd.recv(100)
                    self.login(login_data, sockfd)
                else:
                    self.chat(sock)

    def close_connection(self):
        self.serverSocket.close()