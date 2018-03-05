# -*- coding: utf-8 -*-
import socket
import select
import queue
from . import server_side
import traceback


class ServerSideEpoll(server_side.ChatServer):

    def __init__(self,port=5247):
        server_side.ChatServer.__init__(self)
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind(('0.0.0.0', port))
        self.serverSocket.listen(5)
        self.serverSocket.setblocking(False)

        self.id_to_socket = {}  # socket session字典 id : socket
        self.socket_to_id = {}  # socket session 字典 socket:id
        self.fd_to_socket = {}
        self.message_queues = {}
        self.fd_to_socket[self.serverSocket.fileno()] = self.serverSocket
        self.epoll = select.epoll()
        self.epoll.register(self.serverSocket, select.EPOLLIN)
        # self.message_queues[self.serverSocket.fileno()] = queue.Queue()
        print("server wait for connect....")

    def auth(self,password):
        if password == self.PASSWORD:
            return 0
        else:
            return 1#0登录成功1登录失败

    def login(self,login_data,sock):#新用户登录
        try:
            login_data = sock.recv(100)
            login_data = login_data.decode('utf-8')
            id = login_data.split('||')[0]
            password = login_data.split('||')[1]
        except IndexError as e:
            print(login_data)
            print("in login occured %s"%e)
            self.close_client(sock,self.login.__name__)
        else:
            auth_result = self.auth(password)
            if auth_result == 0:
                print("%s login"%id)
                self.id_to_socket[id] = sock
                self.socket_to_id[sock] = id
                self.message_queues[sock.fileno()] = queue.Queue()
                self.p2psend('',('hello %s,you login successed'%id).encode('utf-8'),id)
            else:
                sock.send("Password inncorrect".encode('utf-8'))
                self.close_client(sock,self.login.__name__)

    def read_data(self, sock):
        data = sock.recv(self.inBufSize)
        data = data.decode('utf-8')
        try:
            remote_id = data.split('||')[0]
            message = data.split('||')[1]
        except IndexError as e:
            print(data)
            print("in read_data occured %s"%e)
            self.close_client(sock,self.read_data.__name__)
        else:
            print("id = %s,message = %s" % (remote_id, message))
            local_id = self.socket_to_id[sock]
            self.pre_send(local_id,message,remote_id)

    def send_2peer(self, sock):
        while True:
            try:
                data = self.message_queues[sock.fileno()].get_nowait()
            except queue.Empty:
                try:
                    self.epoll.modify(sock.fileno(), select.EPOLLIN)
                except FileNotFoundError as e:
                    print(e)
                    print("%s has not registered" % sock.fileno())
                break
            else:
                sock.send(data)

    def pre_send(self, local_id, message, remote_id):
        if remote_id == 'all':
            self.broadcast(local_id, message)
        else:
            self.p2psend(local_id, message, remote_id)

    def broadcast(self, local_id, message):
        for k in self.message_queues:
            message_send = "%s said : %s" % (local_id, message)
            self.message_queues[k].put(message_send)
            self.epoll.modify(k, select.EPOLLOUT)

    def p2psend(self, local_id, message, remote_id):
        try:
            remote_socket = self.id_to_socket[remote_id]
        except KeyError:
            local_socket = self.id_to_socket[local_id]
            local_socket.send("remote %s is offline"%remote_id)
        else:
            message_send = "%s said : %s" % (local_id, message)
            message_send = message_send.encode('utf-8')
            # 把消息放入对应socket的队列
            self.message_queues[remote_socket.fileno()].put(message_send)
            # 修改对应socket为可读
            try:
                self.epoll.modify(remote_socket.fileno(), select.EPOLLOUT)
            except FileNotFoundError as e:
                print(e)
                print("%s has not registered"%remote_socket.fileno())

    # def send_message(self,remote_id,message_send):
    #     # 发送消息
    #     try:
    #         remote_socket = self.id_to_socket[remote_id]
    #         sockfd = remote_socket.fileno()
    #     except KeyError:
    #         pass
    #     else:
    #         # 把消息放入对应socket的队列
    #         self.message_queues[sockfd].put(message_send)
    #         # 修改对应socket为可读
    #         try:
    #             self.epoll.modify(sockfd, select.EPOLLOUT)
    #         except FileNotFoundError as e:
    #             print(e)
    #             print("%s has not registered" % sockfd)


    def socet_handle(self):
        while 1:
            # Get the list sockets which are ready to be read through select
            events = self.epoll.poll(-1)
            if not events:
                continue
            for fd, event in events:
                sock = self.fd_to_socket[fd]
                # 如果活动socket为当前服务器socket，表示有新连接
                if sock == self.serverSocket:
                    # new connection came in
                    connection, addr = self.serverSocket.accept()
                    # 新连接socket设置为非阻塞
                    connection.setblocking(False)
                    # register new to epoll
                    self.epoll.register(connection.fileno(), select.EPOLLIN)
                    self.fd_to_socket[connection.fileno()] = connection
                    try:
                        self.login('', connection)
                    except BaseException:
                        print(traceback.format_exc())
                        self.close_client(connection,self.socet_handle.__name__)
                # 关闭事件
                elif event & select.EPOLLHUP:
                    # 在epoll中注销客户端的文件句柄
                    self.epoll.unregister(fd)
                    # 在字典中删除与已关闭客户端相关的信息
                    try:
                        del self.id_to_socket[self.socket_to_id[self.fd_to_socket[fd]]]
                    except KeyError:
                        pass
                    try:
                        del self.socket_to_id[self.fd_to_socket[fd]]
                    except KeyError:
                        pass
                    # 关闭客户端的文件句柄
                    self.fd_to_socket[fd].close()
                    try:
                        del self.fd_to_socket[fd]
                    except KeyError:
                        pass
                # 可读事件
                elif event & select.EPOLLIN:
                    # 接收数据
                    try:
                        self.read_data(sock)
                    except BaseException:
                        print(traceback.format_exc())
                        self.close_client(sock,self.socet_handle.__name__)
                # 可写事件
                elif event & select.EPOLLOUT:
                    try:
                        self.send_2peer(sock)
                    except BaseException:
                        print(traceback.format_exc())
                        self.close_client(sock,self.socet_handle.__name__)

    def close_connection(self):
        # 在epoll中注销服务端文件句柄
        self.epoll.unregister(self.serverSocket.fileno())
        self.epoll.close()
        self.serverSocket.close()

    def close_client(self,sock, func_name):
        fd = sock.fileno()
        print('close socket %s from %s'%(fd,func_name))
        # 在epoll中注销客户端的文件句柄
        self.epoll.unregister(fd)
        # 在字典中删'除与已关闭客户端相关的信息
        try:
            del self.id_to_socket[self.socket_to_id[self.fd_to_socket[fd]]]
        except KeyError:
            pass
        try:
            del self.socket_to_id[self.fd_to_socket[fd]]
        except KeyError:
            pass
        # 关闭客户端的文件句柄
        self.fd_to_socket[fd].close()
        try:
            del self.fd_to_socket[fd]
        except KeyError:
            pass