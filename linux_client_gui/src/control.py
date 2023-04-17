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

import socket
import nacl.bindings as b
from . import database
import json
import base64
import threading
import time
import traceback
from gi.repository import GLib


def send_cmd(sock, uuid_spk, opc, arg):
    """! Send command to client.
    @param sock   Socket object.
    @param uuid_spk   Speaker UUID.
    @param opc   Command opcode.
    @param arg  Command argument.
    """

    dbcon = database.DB()
    key = base64.b64decode(dbcon.get_keys(uuid_spk)[0][0])
    my_uuid = str(dbcon.get_uuid())

    dict_pkg = {
        "from": my_uuid,
        "to": uuid_spk,
        "cmd": opc,
        "arg": arg
    }

    cipher = encrypt_pkg(key, json.dumps(dict_pkg).encode('utf-8'), my_uuid, uuid_spk)

    send(sock, cipher)



def encrypt_pkg(key, msg, from_u, to_u):
    """! Encrypt string and package crypto.
    @param key   Encryption key.
    @param msg   Message to encrypt.
    @param from_u   Sender UUID.
    @param to_u  Receiver UUID.
    @return  JSON string with encrypted data.
    """

    nonce = b.randombytes(b.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
    add = (from_u+to_u).encode("utf-8")
    cipher = b.crypto_aead_xchacha20poly1305_ietf_encrypt(msg, add, nonce, key)

    print(from_u)

    dict_pkg = {"from": from_u,
        "to": to_u,
        "nonce": base64.b64encode(nonce).decode('utf-8'),
        "ciphertext": base64.b64encode(cipher).decode('utf-8'),
        "pairing_req": False
        }

    return json.dumps(dict_pkg)


def decrypt_pkg(key, json_crypt):
    """! Decrypt JSON string and package crypto.
    @param key   Encryption key.
    @param json_crypt   JSON string of ciphertext.
    @return  Dictionary of plaintext.
    """

    json_crypt = json.loads(json_crypt)

    nonce = base64.b64decode(json_crypt['nonce'])
    cipher = base64.b64decode(json_crypt['ciphertext'])

    additional = (json_crypt['from']+json_crypt['to']).encode('utf-8')

    plaintext = b.crypto_aead_xchacha20poly1305_ietf_decrypt(cipher, additional, nonce, key)

    return json.loads(plaintext)

def start(window, ip):
    """! Connect to server.
    @param window   Corresponding window.
    @param ip   IP of server.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, 6969))
    return s

# helper function for sending
def send(sock, msg):
   sock.send((msg + '\r').encode("utf-8"))

# receive data until CR occurs
def recv(s, timeout = None):
    s.settimeout(timeout)
    a = s.recv(1).decode("utf-8")
    b = ""
    while a != '\r':
        b = b + a
        a = s.recv(1).decode("utf-8")
        if a == "":
            raise Exception()
    if b == "NOK": # if other party signals error
        raise Exception()
    return b

def update(window, socket, uuid_spk):
    """! Update UI elements with info from server.
    @param window   Corresponding Window.
    @param socket   Socket object.
    @param uuid_spk   Speaker UUID.
    """
    try:
        dbcon = database.DB()
        while True:
            key = base64.b64decode(dbcon.get_keys(uuid_spk)[0][0])
            time.sleep(1)
            print("send")
            send_cmd(socket, uuid_spk, "INFO", "")
            print("sent")
            reply = recv(socket, 3)
            print("recvd")
            plaintext = decrypt_pkg(key, reply)
            print(plaintext)

            window.set_pairmode(plaintext['pair'], plaintext['timer'], plaintext['waiting'])

    except:
        traceback.print_exc()
        try:
            GLib.idle_add(window.socket_closed)
        except:
            traceback.print_exc()


def run_infoservice(window, socket, uuid_spk):
    """! Start thread for heartbeat.
    @param window   Corresponding Window.
    @param socket   Socket object.
    @param uuid_spk   Speaker UUID.
    """
    pth = threading.Thread(target=update, args=(window, socket, uuid_spk))
    pth.daemon = True
    pth.start()

