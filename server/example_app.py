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

import threading
import driver.database as db
import socket
import json
import driver.database as db
import base64
import traceback
import nacl.bindings as b
import driver.pairing_thread as pt
import time
import subprocess
import signal
import prctl
import driver.sock_server.put_get as pg
from driver.sock_server.sock_ops import sock_write, sock_read
import config

# This module implements the example play song feature
# as well as arbiting pairing requests

# timer for pairing time window
timer_rem = 0

# flag to signal that pairing has been allowed between threads
pairing_allow = threading.Semaphore(0)

# keep time during which pairing is allowed
# time is counted down by this thread
# TODO: Remove countdown - just store time at which pairing will 
#       be disallowed and check against it
def timer_thread():
    global timer_rem
    while True:
        if(timer_rem > 0):
            timer_rem = timer_rem - 1
        time.sleep(1)



# This function is called as a thread
# The function tests for incoming client connections and creates
# a thread handling each connection
def main_socket_server(sck):

    while(True):
        # allow 10 concurrent connections
        sck.listen(10)
        # accept incoming connection
        temp_conn_socket = sck.accept()

        # create handler thread
        tth = threading.Thread(target=client_thread, args=(temp_conn_socket[0],))
        tth.daemon = True
        tth.start()

# Teardown function
def close():
    # ignore all erors here
    try:
        # stop listening
        main_socket.close()
    except:
        pass

# Init function
# creates all necessary threads
def init():
    # start listening
    global main_socket
    main_socket = socket.create_server(("", config.get_conf('example_port')), family=socket.AF_INET6, dualstack_ipv6=True)

    # create thread which handles incoming connections
    pth = threading.Thread(target=main_socket_server, args=(main_socket,))
    pth.daemon = True
    pth.start()

    # create timer thread
    # TODO: May be removed, see above
    tth = threading.Thread(target=timer_thread)
    tth.daemon = True
    tth.start()

    # create thread handling pairing requests
    cth = threading.Thread(target=check_pairing_requested)
    cth.daemon = True
    cth.start()

# Send encrypted and authenticated JSON package
def encrypt_pkg(key, msg, from_u, to_u):
    # create NONCE
    nonce = b.randombytes(b.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
    # add uuid of sender and receiver as header data
    # will be authenticated but not encrypted
    add = (from_u+to_u).encode("utf-8")
    # encrypt
    cipher = b.crypto_aead_xchacha20poly1305_ietf_encrypt(msg, add, nonce, key)

    # create final JSON string containing header, nonce and cipher
    dict_pkg = {"from": from_u, 
        "to": to_u,
        "nonce": base64.b64encode(nonce).decode('utf-8'),
        "ciphertext": base64.b64encode(cipher).decode('utf-8')
        }

    return json.dumps(dict_pkg)

# decrypt received JSON packet
def decrypt_pkg(key, json_crypt):

    # check that receipient matches
    #if json_crypt['to'] != db.DB().get_uuid():
    #    raise Exception("Wrong receipient")
    
    # get nonce and ciphertext
    nonce = base64.b64decode(json_crypt['nonce'])
    cipher = base64.b64decode(json_crypt['ciphertext'])

    # regenerate header
    additional = (json_crypt['from']+json_crypt['to']).encode('utf-8')

    # decrypt
    plaintext = b.crypto_aead_xchacha20poly1305_ietf_decrypt(cipher, additional, nonce, key)

    return json.loads(plaintext)

# handles single client connection
def client_thread(sock):
    print("new connection")
    dbcon = db.DB()

    try:
        # loop over all commands from client
        while True:
            # get command
            repl = sock_read(sock).replace("\n","")
            # disassemble JSON
            json_crypt = json.loads(repl)
            # retrieve decryption key
            key = base64.b64decode(dbcon.get_keys(json_crypt['from'])[0][0])
            # decrypt
            command = decrypt_pkg(key, json_crypt)
            # evaluate command
            parse_cmd(command, sock)
    except:
        # on error, close the socket and print error
        # ignore further exceptions
        try:
            sock.close()
            traceback.print_exc()
        except:
            pass

# wait for clients to connect to the pairing port
# called as thread
def check_pairing_requested():
    while True:
        pg.sock_launch_and_wait()
        if db.DB().num_users() > 0:
            pair_req()

# evaluate pairing request
mutex_single_pair = threading.Lock()
def pair_req():
    global timer_rem

    # only allow single entry here
    with mutex_single_pair:
        try:
            # check pair mode currently used
            dbcon = db.DB()
            mode = dbcon.get_pairmode()

            # if always, just allow
            if(mode == "always"):
                pt.request_pairing()
                pg.sock_write("OK")
                
            # if timer, check that time has not elapsed
            if(mode == "timer"):
                if(timer_rem > 0):
                    pt.request_pairing()
                    pg.sock_write("OK")
                else:
                    pg.sock_write("KO")

            # if explicit, ask other client for acceptance
            if(mode == "explicit"):
                pg.sock_write("EX")
                try:
                    print("waiting for sem")
                    acquired = False
                    for i in range(60): # wait for 60 seconds and fail afterwards
                        # test allowance
                        acquired = pairing_allow.acquire(timeout=1) # wait for allow
                        if acquired:
                            break
                        # test socket
                        # if socket breaks, pairing shall be freed for further clients
                        # we must send a char here, otherwhise an abort from the client will
                        # be undetected
                        pg.sock_raw(".")

                    # if no one accepted, error out
                    if not acquired:
                        raise Exception("No acq")
                    
                    print("acquired")
                    pg.sock_write("OK")
                except:
                    traceback.print_exc()
                    print("error")
                    pg.sock_write("NOK")
        except:
            pass

# sends information about the current state to the client
def send_info(sock, uuid_cli, uuid_us):
    dbcon = db.DB()
    key = base64.b64decode(dbcon.get_keys(uuid_cli)[0][0])

    info = {
        "pair": dbcon.get_pairmode(), # pairing mode
        "waiting": mutex_single_pair.locked(), # anyone waiting? (explicit mode)
        "timer": timer_rem # remaining time (timer mode)
        }

    info_s = json.dumps(info) # create JSON

    # encrypt and send
    cipher = encrypt_pkg(key, info_s.encode('utf-8'), uuid_us, uuid_cli)
    sock_write(sock, cipher)

# hold mplayer instance
player = None

mutex_single_cmd = threading.Lock()
def parse_cmd(command, sock):
    global timer_rem
    global player

    # make sure cmds are parsed one at a time
    with mutex_single_cmd:

        # get command components
        opcode = command["cmd"]
        arg = command["arg"]
        from_uuid = command["from"]
        to_uuid = command["to"]
        dbcon = db.DB()

        # setting pairmode
        if(opcode == "PMOD"):
            print(arg)
            dbcon.write_setting("pair_mode", arg)

        # allow pairing
        if(opcode == "PAIRALLOW"):
            mode = dbcon.get_pairmode()
            if(mode == "explicit"):
                pairing_allow.release()
                pt.request_pairing()
            if(mode == "timer"):
                timer_rem = 60*5 # 5 minute cooldown

        #play song
        if(opcode == "PLAY"):
            if(player != None):
                player.terminate()
            player = subprocess.Popen(["mplayer", "-ao", "sdl", "audio/example_song.mp3"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL))

        # stop playback
        if(opcode == "STOP"):
            if(player != None):
                player.terminate()
                player = None

        # louder
        if(opcode == "MORE"):
            if(player != None):
                player.stdin.write("*".encode('utf-8'))
                player.stdin.flush()

        # quieter
        if(opcode == "LESS"):
            if(player != None):
                player.stdin.write("/".encode('utf-8'))
                player.stdin.flush()

        # request info
        if(opcode == "INFO"):
            send_info(sock, from_uuid, to_uuid)