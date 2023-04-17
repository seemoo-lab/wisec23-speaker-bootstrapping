#!/usr/bin/env python

#
#Copyright (C) 2022 SEEMOO Lab TU Darmstadt (mscheck@seemoo.tu-darmstadt.de)
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

"""
example modified from: https://gist.github.com/BenKnisley/5647884
"""
import socket, time, select

s = None

# send data, end is marked by CR
def send(D):
   s.send((D + '\r').encode("utf-8"))

# wait for available data and discard keepalive char
# returns true if data is available
# otherwise false
# if no keepalive from the other side occurs, abort
def check_data_avail():

    avail = select.select([s],[],[],5)[0]
    if avail:
        a = s.recv(1, socket.MSG_PEEK)
        if a == b'.':
            s.recv(1)
            return False
        return True
    else:
        raise Exception("No keepalive. Broken pipe.")

# receive data until CR occurs
def recv(timeout=None):
    a = s.recv(1).decode("utf-8")
    b = ""
    while a != '\r':
        b = b + a
        a = s.recv(1).decode("utf-8")
    if b == "NOK": # if other party signals error
        raise Exception()
    return b

# close connection
def close():
    global s
    s.shutdown(socket.SHUT_WR)
    s.close()
    s = None

# connect to speaker
# default IP and port for pairing
def setup(ip="10.42.0.1", port=17099):
    global s
    print(ip)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
