# -*- coding: utf-8 -*-
import select
from backends import server_side_epoll
from backends import server_side_select

def main():
    if hasattr(select, 'epoll'):
        sub_obj = server_side_epoll.ServerSideEpoll()
    else:
        sub_obj = server_side_select.ServerSideSelect()
    sub_obj.start()

if __name__ == '__main__':
    main()