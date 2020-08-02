import argparse
import socket
import sys
import struct
import json

SERVERPORT = 9000
RECVHEADLEN = 4
SENDHEADLEN = 2

def recvall(sock : socket.socket) -> (bool, bool, bytes):
    head = b""
    while len(head) < RECVHEADLEN:
        more = sock.recv(RECVHEADLEN - len(head))
        if not more:
            raise Exception("传输出错：数据传输尚未完成，但连接断开")
        head += more
    data_len, success, end = struct.unpack("!H??", head)
    data = b""
    while len(data) < data_len:
        more = sock.recv(data_len - len(data))
        if not more:
            raise Exception("传输出错：数据传输尚未完成，但连接断开")
        data += more
    return success, end, data

def addHead(data : bytes) -> bytes:
    if SENDHEADLEN == 2:
        data_len = struct.pack("!H", len(data))
        return (data_len + data)
    else:
        raise Exception("添加包头失败，当前允许的包头长度为：", SENDHEADLEN)

def send(sock : socket.socket, request : dict):
    body = json.dumps(request).encode("utf-8")
    sock.sendall(addHead(body))

def getArgs() -> (int, str, str, str):
    parser = argparse.ArgumentParser(description = "用于从服务器下载文件")
    parser.add_argument("-p", dest = "port", type = int, default = SERVERPORT, 
        help = "指定文件下载服务器端口，默认端口为{}".format(SERVERPORT))
    parser.add_argument("host", help = "远程服务器主机名")
    parser.add_argument("remote_file", help = "将要下载的文件下载服务器文件")
    parser.add_argument("local_file", help = "文件下载成功后重命名为此名称")
    args = parser.parse_args()
    return args.port, args.host, args.remote_file, args.local_file

def connectServer(host : str, port : int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except Exception:
        sys.exit("连接服务器失败，请检查输入主机和端口是否正确，然后重新输入")
    else:
        return sock

def downloadFile(sock : socket.socket, remote_file : str, local_file :str):
    """
    request = {
        "type" : "download",
        "filename" : filename
    }
    response: 211....
    2:包体长度
    1:sucess
    1:end
    """
    request = {}
    request["type"] = "download"
    request["filename"] = remote_file
    send(sock, request)
    success, end, recv_data = recvall(sock)
    if success:
        f = open(local_file, "wb")
        f.write(recv_data)
        while True:
            if not end:
                success, end, recv_data = recvall(sock)
                f.write(recv_data)
            else:
                f.close()
                break
    else:
        sys.exit("服务器没有此文件，请确定文件名是否正确，然后重新输入")

def main():
    port, host, remote_file, local_file = getArgs()
    sock = connectServer(host, port)
    downloadFile(sock, remote_file, local_file)
    sock.close()

    

main()
