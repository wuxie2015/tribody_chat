# -*- coding: utf-8 -*-
import threading
import logging
import os
from logging.handlers import RotatingFileHandler


class ChatServer(threading.Thread):
    inBufSize = 4096
    outBufSize = 4096
    CONNECTION_LIST = []
    PASSWORD = '123456'  # 先暂时设置一个，以后放到数据库里

    def __init__(self):
        threading.Thread.__init__(self)
        self.logger = self.logger_init()

    def logger_init(self):
        # 定义一个RotatingFileHandler，最多备份5个日志文件，每个日志文件最大10M
        log_file = 'server_side.log'
        log_path = os.path.join(os.getcwd(), 'log', log_file)
        Rthandler = RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
        Rthandler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '\n%(asctime)s   %(filename)s[line:%(lineno)d]   %(levelname)s\n%(message)s')
        Rthandler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(Rthandler)
        logger.setLevel(logging.DEBUG)
        return logger


    def auth(self,password):
        # 用户登录鉴权
        pass

    def login(self,login_data,sock):
        # 用户登录
        pass

    def pre_send(self,local_id,message,remote_id):
        pass

    def p2psend(self,local_id,message,remote_id):
        pass

    def broadcast(self,local_id,message):
        pass

    def socet_handle(self):
        pass

    def close_connection(self):
        pass

    def run(self):
        self.socet_handle()