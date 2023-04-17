
import socket, time
import driver.sock_server.sock_ops as so


temp_conn_socket = None # socket for comms w user
main_socket = None # socket for listening server

def Tcp_server_init(port=17099, ip='0.0.0.0'):
    global main_socket
    global temp_conn_socket
    temp_conn_socket == None
    if main_socket == None:
        main_socket = socket.create_server(("", port), family=socket.AF_INET6, dualstack_ipv6=True)

# wait, allow n connections
def Tcp_server_wait(numofclientwait):
    global main_socket
    main_socket.listen(numofclientwait) 

# get first waiting connection
def Tcp_server_next():
    global temp_conn_socket
    temp_conn_socket = main_socket.accept()[0]

# wait with timeout for reply
def sock_wait_reply(timeout = None):
    return so.sock_read(temp_conn_socket, timeout)

# wait for connection
def sock_launch_and_wait():
    Tcp_server_wait (1)
    Tcp_server_next()

def wait_sock_avail():
    global temp_conn_socket
    temp_conn_socket = None
    while temp_conn_socket == None:
        time.sleep(0.2)

# write data
def sock_write(data):
    if temp_conn_socket != None:
        so.sock_write(temp_conn_socket, data)

# write data without framing
def sock_raw(D):
    if temp_conn_socket != None:
        temp_conn_socket.sendall((D).encode("utf-8")) 

# stop allowing connections
def sock_close():
    global main_socket
    if main_socket != None:
        main_socket.listen(0)

# close socket
def sock_teardown():
    global main_socket
    global temp_conn_socket
    if temp_conn_socket != None:
        temp_conn_socket.close()
        temp_conn_socket = None
    if main_socket != None:
        main_socket.close()
        main_socket = None
