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

import driver.tts as tts
import driver.wifi.wifi_control as ap
import driver.sock_server.put_get as pg
import driver.ecdh as dh
import driver.acoustic as ac
import driver.database as db
import random
import string
import config
import lang
import base64
import traceback
import time
import uuid as uuid_lib
import json
import os
import random
from functools import reduce
from shlex import quote
import subprocess
import nacl.bindings as b
import socket
from driver.button import accept_or_reject

# word file for secret verification
word_file = "/usr/share/dict/cracklib-small"

# decrypt and decode a settings packet
def decode_setting_pkg(keys, timeout):
    # read text
    network_enc = pg.sock_wait_reply(timeout)
    debug(f"Ciphertext: {network_enc}")

    # get nonce and ciphertext
    json_crypt = json.loads(network_enc)
    nonce = base64.b64decode(json_crypt['nonce'])
    cipher = base64.b64decode(json_crypt['ciphertext'])

    # decrypt
    plaintext = b.crypto_aead_xchacha20poly1305_ietf_decrypt(cipher, b"", nonce, keys[b'encrypt'])

    return json.loads(plaintext)

# remove all NetworkManager settings and start access point
def initial_nw_setup(ap_name, pairing_pin):
    ap.purge_nm()
    ap.launch_ap(ap_name, pairing_pin)

# generate random string of length places
def random_string(places):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=places))

# bytes to base64 string
def b2b64str(bytestring_to_convert):
    return base64.b64encode(bytestring_to_convert).decode("utf-8")

# debug prints
def debug(str):
    pass

# main pairing function
# requires UUID of speaker
# if initial or subsequent

def pair(uuid, initial = True):
    try:
        dbcon = db.DB()
        ## generate session tokens
        # random suffix for access point name
        ap_random = random_string(config.get_conf('network_randoms'))
        # full AP name
        ap_name = config.get_conf('network_prefix') + ap_random
        # PSK for AP network
        ap_pass = random_string(config.get_conf('pin_randoms'))
        # pairing secret for networked pairing
        n_pairing_secret = random_string(config.get_conf('network_randoms')+config.get_conf('pin_randoms'))
            
        # differentiate between initial and networked pairing voice welcome
        if initial:
            tts.say(lang.get_string('connect_msg_ini'))
        else:
            tts.say(lang.get_string('connect_msg_sub'))

        # Create own dh secret
        speaker_dh_pkey = dh.gen_key()
        debug(f"DH key: {speaker_dh_pkey}")

        # create hash over dh key and uuid for initial message
        data_to_hash = speaker_dh_pkey.encode("utf-8") + str(uuid).encode('utf-8')
        uuid_dh_hash = b.crypto_generichash_blake2b_salt_personal(data_to_hash, digest_size=16)

        # either send network parameters or pairing secret depending on pairing mode
        if initial:
            ac.transmit_message("I" + b2b64str(uuid_dh_hash) + ap_random + ap_pass, loop=True, stop_prev=True)
        else:
            ac.transmit_message("N" + b2b64str(uuid_dh_hash) + n_pairing_secret, loop=True, stop_prev=True)


        # Launch AP and HTTP server if initial
        if initial:
            initial_nw_setup(ap_name, ap_pass)
            pg.wait_sock_avail()

        # send uuid and public key to client
        pg.sock_write(str(uuid))
        pg.sock_write(speaker_dh_pkey)

        # wait for client reply
        if initial:
            # with timeout
            client_uuid_plain = pg.sock_wait_reply(5.0)
        else:
            # without timeout as acoustic msg must be read
            client_uuid_plain = pg.sock_wait_reply()

        client_dh_key = pg.sock_wait_reply(1.0) # wait with timeout for clients key

        debug(f"Got from cli: UUID {client_uuid_plain} DH {client_dh_key}")

        # get data from client
        client_name = pg.sock_wait_reply(5.0)
        client_mac_b64 = pg.sock_wait_reply(5.0)
        client_mac = base64.b64decode(client_mac_b64)

        debug(f"Got from cli: Name {client_name} MAC {client_mac_b64}")

        # defer keys
        keying_material = dh.exchange_key(client_dh_key)
        keys = dh.defer_keys(keying_material)
        keys_b64 = list(map(base64.b64encode, keys.values()))
        keying_mat_b64 = base64.b64encode(keying_material)

        debug(f"master secret: {keying_mat_b64}")
        debug(f"keys: {keys_b64[0]} {keys_b64[1]} {keys_b64[2]}")

        verify = None
        # regenerate client signature
        if initial:
            verify = client_uuid_plain + client_dh_key + client_name
        else:
            verify = client_uuid_plain + client_dh_key + client_name + n_pairing_secret

        # check if MAC fits data and derived key
        # first step in assuring correct key exchange
        b.crypto_auth_verify(client_mac, verify.encode('utf-8'), keys[b'sign'])

        # stop pairing code
        ac.stop_transmit()

        # ask user to physically confirm pairing
        tts.say(lang.get_string('cli_name_pre'))
        tts.say(client_name)
        tts.say(lang.get_string('cli_name_post'))

        # check confirmation
        user_allow_pairing_str = input("[Y/N]")
        if (user_allow_pairing_str != 'Y' and user_allow_pairing_str != 'y'):
        

        ## FreeSpeaker code
        #if not accept_or_reject(3):
            tts.say(lang.get_string('abort'))
            raise Exception("User abort")

        tts.say(lang.get_string('confirmed'))

        pg.sock_write("OK")

        # loud and clear key verification

        # read word list
        words = open(word_file).read().splitlines()
        
        # select word
        sel = b.randombytes_buf_deterministic(4, keys[b'verify'])

        debug(sel)

        # get random words
        result = 0
        for i in range(4):
            result = int(result) | ( (int(sel[i]) & 0xff ) << (8 * i) )
        result = result % len(words)
        chosen_word = words[result]

        tts.say(lang.get_string('tutorial_word_selection'))
        # read string until user confirms
        while True:
            try:
                tts.say(chosen_word)
                pg.sock_wait_reply(0.5)
                break
            except socket.timeout as e:
                pass


        if initial:
            # get network+additional settings from client
            nw_settings = decode_setting_pkg(keys, 60)

            # stop http server after getting reply
            pg.sock_close()

            ap.stop_ap() # stop own access point

            # wifi connection stage
            # try until abort or successful connection
            while True:
                try:
                    # scan and connect via NM
                    print("scanning networks:")
                    ap.wait_wifi_network(nw_settings['name'], 60) # try to find network
                    print("connecting via NM:")
                    # try to connect and check success
                    return_value = subprocess.check_output("nmcli dev wifi connect " + quote(nw_settings['name']) + " password " + quote(nw_settings['key']), shell=True)
                    print(return_value)
                    if ("Error" in return_value.decode("utf-8")):
                        raise Exception()
                    print(f"retval: {return_value}")
                    break
                except:
                    # retry with new parameters if failed
                    tts.say(lang.get_string('wifi_fail'))
                    # restart ap and server
                    initial_nw_setup(ap_name, ap_pass)
                    pg.sock_launch_and_wait()
                    # get new settings
                    nw_settings = decode_setting_pkg(keys, 60)
                    # close AP and socket
                    pg.sock_close()
                    ap.stop_ap()
                    time.sleep(5) # give client time to detect missing AP
                    


            # store name of chosen wifi (although NM will always connect automatically)
            dbcon.write_setting("wifi",  nw_settings['name'])
            # save speakers name
            dbcon.write_setting("name",  nw_settings['host'])

        else:
            pg.sock_close()

        tts.say(lang.get_string('pair_done'))
        return (True, client_uuid_plain, keys_b64, client_name)
    except:
        #teardown
        traceback.print_exc() # print which error occured
        try:
            pg.sock_write("NOK") # tell client to abort
        except:
            pass
        # stop acoustic, AP and socket
        pg.sock_close()
        ap.stop_ap()
        ac.stop_transmit()

        # voice cues
        if initial:
            tts.say(lang.get_string('pair_fail_ini'))
        else:
            tts.say(lang.get_string('pair_fail'))

        return (False,)
