import struct
import json
import socket
import select
import argparse

SERVERPORT = 9000
RECVHEADLEN = 2
SENDHEADLEN = 4
MAXBYTES = 512

def recvall(sock : socket.socket) -> bytes:
    head = b""
    while len(head) < RECVHEADLEN:
        more = sock.recv(RECVHEADLEN - len(head))
        if not more:
            raise Exception("传输出错：数据传输尚未完成，但连接断开")
        head += more
    data_len, = struct.unpack("!H", head)
    data = b""
    while len(data) < data_len:
        more = sock.recv(data_len - len(data))
        if not more:
            raise Exception("传输出错：数据传输尚未完成，但连接断开")
        data += more
    return data

def send(sock : socket.socket, success : bool, end : bool, data : bytes):
    head = struct.pack("!H??", len(data), success, end)
    while True:
        try:
            sock.sendall(head + data)
        except BlockingIOError:
            #系统尚未准备好发送
            continue
        else:
            break


def recv(sock : socket.socket) -> dict:
    request = recvall(sock)
    request = json.loads(request.decode("utf-8"))
    return request

def createSocket(server_ip : str, server_port : int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((server_ip, server_port))
    sock.listen(5)
    sock.setblocking(0)
    return sock

def remove(sock : socket.socket, sock_list : list, filename : dict):
    #从 sock_list filename 移除 sock，顺便关闭 sock
    sock_list.remove(sock)
    filename.pop(sock)
    sock.close()

def getArgs() -> (int, str):
    parser = argparse.ArgumentParser(description = "启动服务器")
    parser.add_argument("-p", dest = "port", type = int, default = SERVERPORT, 
        help = "指定文件下载服务器端口，默认端口为{}".format(SERVERPORT))
    parser.add_argument("host", help = "将要绑定的服务器IP地址")
    args = parser.parse_args()
    return args.port, args.host

def asynDownloadFile(sock : socket.socket):
    sock_list = [sock] # [socket.socket]
    filename = {} # {socket.socket : str(filename)}
    while True:
        read, write, err = select.select(sock_list, sock_list, sock_list)
        for sc in read:
            #首先处理读
            if sc == sock:
                #有新连接
                new_sock, addr = sc.accept()
                sock_list.append(new_sock)
                filename[new_sock] = None
            else:
                #客户端发送请求
                try:
                    request = recv(sc)
                except Exception:
                    #客户端连接断开
                    remove(sc, sock_list, filename)
                else:
                    filename[sc] = request["filename"]
        
        for sc in write:
            #然后处理写，发送数据
            sc_filename = filename[sc]
            try:
                f = open(sc_filename, "rb")
            except FileNotFoundError:
                send(sc, 0, 1, b"")
                remove(sc, sock_list, filename)
            else:
                success = 1
                while True:
                    send_data = f.read(MAXBYTES)
                    if len(send_data) == MAXBYTES:
                        #没到结尾
                        end = 0
                        send(sc, success, end, send_data)
                    else:
                        #到了结尾
                        end = 1
                        send(sc, success, end, send_data)
                        f.close()
                        remove(sc, sock_list, filename)
                        break




def main():
    port, host = getArgs()
    sock = createSocket(host, port)
    asynDownloadFile(sock)

main()