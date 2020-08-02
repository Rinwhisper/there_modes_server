import struct
import json
import socket
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
    sock.sendall(head + data)


def recv(sock : socket.socket) -> dict:
    request = recvall(sock)
    request = json.loads(request.decode("utf-8"))
    return request

def createSocket(server_ip : str, server_port : int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((server_ip, server_port))
    sock.listen(5)
    return sock

def getArgs() -> (int, str):
    parser = argparse.ArgumentParser(description = "启动服务器")
    parser.add_argument("-p", dest = "port", type = int, default = SERVERPORT, 
        help = "指定文件下载服务器端口，默认端口为{}".format(SERVERPORT))
    parser.add_argument("host", help = "将要绑定的服务器IP地址")
    args = parser.parse_args()
    return args.port, args.host

def downloadFile(sock : socket.socket):
    request = recv(sock)
    if request["type"] == "download":
        filename = request["filename"]
        try:
            f = open(filename, "rb")
        except FileNotFoundError:
            send(sock, 0, 1, b"")
        else:
            success = 1
            while True:
                send_data = f.read(MAXBYTES)
                if len(send_data) == MAXBYTES:
                    #没到结尾
                    end = 0
                    send(sock, success, end, send_data)
                else:
                    #到了结尾
                    end = 1
                    send(sock, success, end, send_data)
                    f.close()
                    sock.close()
                    break

    else:
        raise Exception("发生了未知的错误，请求类型错误")

def main():
    port, host = getArgs()
    sock = createSocket(host, port)
    while True:
        sc, addr = sock.accept()
        downloadFile(sc)

main()