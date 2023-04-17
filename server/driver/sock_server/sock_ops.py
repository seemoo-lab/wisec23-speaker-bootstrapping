import socket

# fuctions for start and end detection during socket xmission

# write data to socket and append \r
def sock_write(socket, data):
    if socket != None:
        socket.sendall((data + '\r').encode("utf-8")) 

# read until \r is encountered
def sock_read(socket, timeout = None):
    b = ""
    socket.settimeout(timeout)
    a = socket.recv(1).decode("utf-8")
    while a != '\r':
        b = b + a
        a = socket.recv(1).decode("utf-8")
    socket.settimeout(None)
    if b.replace(".","") == "NOK":
        raise Exception()
    return b
