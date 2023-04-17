import driver.acoustic as ac
import config
import os

import requests

import driver.ecdh as dh
import driver.sock_cli as cli
import uuid as uuid_lib

import base64

import socket

import json

import nacl.bindings as b

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

import time

import getpass

import random

import subprocess

from shlex import quote

import traceback


# file used to generate verification words
word_file = "/usr/share/dict/cracklib-small"

# helper function to list wifi networks with NMcli
def get_wifi_networks():
    results = subprocess.check_output(["nmcli", "-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes"])
    results = results.decode("ascii") # needed in python 3
    results = results.replace("\r","")
    ls = results.split("\n")
    return ls

# waits with timeout until a wifi network becomes available
def wait_wifi_network(net_name, timeout):
    start = time.time()
    while True:
        if (time.time() - start > timeout):
            raise Exception("Timeout occured!")
        nw_list = get_wifi_networks()
        if net_name in nw_list:
            break

# check if a network is available
def check_wifi_network(net_name):
    nw_list = get_wifi_networks()
    if net_name in nw_list:
        return True
    return False

# send a dictionary as JSON and encrypted+authenticated to the server
def json_send(nw_dict, keys):
    json_nw = json.dumps(nw_dict)

    nonce = b.randombytes(b.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
    ciphertext = b.crypto_aead_xchacha20poly1305_ietf_encrypt(str(json_nw).encode("utf-8"), b"", nonce, keys[b"encrypt"])

    json_k = [ 'nonce', 'ciphertext' ]
    json_v = [ base64.b64encode(x).decode('utf-8') for x in [nonce, ciphertext] ]
    nwconfig_send = json.dumps(dict(zip(json_k, json_v)))

    cli.send(nwconfig_send)

# bytestring to base64 string
def b2b64str(bytestring_to_convert):
    return base64.b64encode(bytestring_to_convert).decode("utf-8")

if __name__ == "__main__":
    
    try:
        # generate a client UUID for use with this speaker
        # TODO: use sqlite like in server
        uuid = uuid_lib.uuid4()

        # holds found Zeroconf/Bonjour devices
        found = None

        # listener for service browsing
        class NetworkedSpeakerListener(ServiceListener):
            # necessary to avoid exceptions
            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass
            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

            # if a unpaired Zeroconf device is found, store it
            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                global found
                info = zc.get_service_info(type_, name)
                found = (socket.inet_ntoa(info.addresses[0]), info.properties[b"uuid"].decode("utf-8"))
                print("found zeroconf")

        print("scanning pairing code and looking for zeroconf devices if any")

        # start listening
        zeroconf = Zeroconf()
        listener = NetworkedSpeakerListener()
        # TODO: move prefix to config
        browser = ServiceBrowser(zeroconf, "_SEEMOOSPEAKER._tcp.local.", listener)

        # start decoding audio message
        ac.decode_start()

        # holds received audio msg
        str_msg = None
        # holds detected pairing type (initial/networked)
        pair_type = None
        while True:
            # poll audio message reception
            str_msg = ac.decode_poll()
            # if the received msg signifies initial pairing
            # continue with this mode
            if str_msg != None and str_msg[0] == "I":
                pair_type = "initial"
                break
            # if a networked speaker was found, continue this way
            if found != None:
                pair_type = "networked"
                ac.decode_stop() # stop pairing reception early
                break

        # for network pairing, we need to scan another code
        if(pair_type == "networked"):
            ac.decode_start()
            while True:
                str_msg = ac.decode_poll()
                # make sure type is networked
                if str_msg != None and str_msg[0] == "N":
                    break

        # tell user about selected pairing mode
        print(f"pair type {pair_type}")

        #dissecting initial message

        # calculate lengths
        len_pin = config.get_conf('pin_randoms')
        len_nw = config.get_conf('network_randoms')
        len_ps = len_pin + len_nw

        # for both, extract hash over DH and UUID components of speaker
        uuid_dh_hash = str_msg[1:-len_pin-len_nw]
        print(uuid_dh_hash)
        # for initial pairing, get WiFi name and PSK
        wifi_pass = str_msg[-len_pin::]
        wifi_name = config.get_conf('network_prefix') + str_msg[-len_pin-len_nw:-len_pin]
        # for followup networked pairing extract secret
        n_secret = str_msg[-len_ps::]

        if (pair_type == "initial"):
            print("scanning networks:")
            # look for the AP created by the speaker
            # timeout after 60 seconds
            # TODO: move timeout to config
            wait_wifi_network(wifi_name, 60)
        
            print("connecting via NM:")
            # connect to wifi
            # TODO: move to subprocess
            os.system("nmcli dev wifi connect " + quote(wifi_name) + " password " + quote(wifi_pass))

        client_pubkey = dh.gen_key() # generate ecdh keypair
        client_uuid_str = str(uuid) # convert uuid to network-transferrable representation

        # exchange ECDH keys
        if pair_type == "initial":
            cli.setup() # connect to default IP set by initial access point
        else:
            cli.setup(found[0]) # connect to IP given by user network to speaker
        cli.send(client_uuid_str) # send client UUID to speaker
        cli.send(client_pubkey) # send client pubkey to speaker
        
        # get UUID and ECDH from speaker
        speaker_uuid_plain = cli.recv()
        speaker_key = cli.recv()

        #hash
        data_to_hash = speaker_key.encode("utf-8") + speaker_uuid_plain.encode('utf-8')
        uuid_dh_hash_cmp = b.crypto_generichash_blake2b_salt_personal(data_to_hash, digest_size=16)

        # check hashes for equality
        uuid_dh_hash = base64.b64decode(uuid_dh_hash)
        if(uuid_dh_hash_cmp != uuid_dh_hash):
            cli.send("NOK") # NOK signifies abort to speaker
            raise Exception("Mismatch between acoustic and wifi hash values for speaker!")

        # derive keys
        keying_material = dh.exchange_key(speaker_key) # exchange ECDH components
        keys = dh.defer_keys(keying_material) # uses HKDF for key derivation

        cli.send(socket.gethostname()) # tell speaker my name

        # Sign our previously sent data with the derived signature key. This proves that derived keys are equal
        if pair_type == "initial":
            msg = b.crypto_auth((client_uuid_str + client_pubkey + socket.gethostname()).encode("utf-8"), keys[b'sign'])
            #msg = digest(keys[b'sign'], (client_uuid_b64str + client_publey + socket.gethostname()).encode("utf-8"), "sha256")
        else:
            # here the client also proves that he received the secret in the audio message fromthe speaker and must therefore be close
            msg = b.crypto_auth((client_uuid_str + client_pubkey + socket.gethostname() + n_secret).encode("utf-8"), keys[b'sign'])
            #msg = digest(keys[b'sign'], (client_uuid_b64str + client_publey + socket.gethostname() + n_secret).encode("utf-8"), "sha256")

        cli.send(b2b64str(msg))

        reply = cli.recv() #server may abort here if hash is broken (abort implemented in recv function)
        reply = cli.recv()

        # Loud&clear style verification
        # pick words at random from a file
        # rng is initialized with verify key
        if True:
            random.seed(keys[b"verify"])
            # file is closed as object directly falls out of context
            words = open(word_file).read().splitlines()
            sel = b.randombytes_buf_deterministic(4, keys[b'verify'])
            print(sel)
            result = 0
            for i in range(4):
                result = int(result) | ( (int(sel[i]) & 0xff ) << (8 * i) )
            result = result % len(words)
            chosen_word = words[result]

            # draw words
            #for i in range(8):
            #    sel = random.randrange(0, len(words)-1)
            #    chosen_words.append(words[sel])
            # show and ask user
            print(chosen_word)
            verify_reply = input("Pattern matches? [Y/N]:")
            if(verify_reply != 'Y' and verify_reply != 'y'):
                cli.send('NOK')
            cli.send("OK")

        # Send settings struct to speaker
        # TODO: Decouple network config and verification settings/speaker naming to simplify code here
        # TODO: Move strings to config
        nw_dict = {}
        if(reply == "NW"):
            # collect and store user input
            print("Network setup requested! (WPA2 only currently!)")
            hostn = input("Hostname (Speaker):")
            nname = input("SSID: ")
            npass = getpass.getpass("KEY: ")
            nw_dict["name"] = nname
            nw_dict["key"] = npass
            nw_dict["host"] = hostn
        
        # send settings as encrypted JSON
        json_send(nw_dict, keys)

        

        cli.close() # done talkimg to speaker
        

        # on first setup, speaker must connect to wifi
        if pair_type == "initial":
            # delete and deassociate connection to speaker
            print("disconnecting")
            os.system("nmcli con down id " + quote(wifi_name))
            os.system("nmcli con delete " + quote(wifi_name))

            print("start service browsing and failover wifi search")

            class NewSpeakerListener(ServiceListener):
                # necessary to avoid exceptions
                def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    pass
                def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    pass

                # wait for correct speaker to get found
                def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    global found
                    info = zc.get_service_info(type_, name)
                    if(info.properties[b"uuid"].decode("utf-8") == str(speaker_uuid_plain)):
                        ip = info.addresses[0]
                        found = (socket.inet_ntoa(info.addresses[0]), info.properties[b"uuid"].decode("utf-8"))

            # wait some time as speaker needs time to connect
            time.sleep(10)

            # start browsing
            zeroconf = Zeroconf()
            listener = NewSpeakerListener()
            browser = ServiceBrowser(zeroconf, "_SEEMOOSPEAKER._tcp.local.", listener)
            vanished = False # as networkmanager sometimes has ghost networks in its scanlist,
                # we wait for the network to disapper, then reappear for failover

            # failover: if speaker cannot connect, it will spin up the AP again and wait for new data
            # TODO: This block will be unnecessary once wifi and other settings are decoupled
            try:
                
                while (found == None):
                    if (reply == "NW"):
                        # if network disappears we are ready to wait for reappearing
                        if check_wifi_network(wifi_name) == False and vanished == False:
                            vanished = True
                        # if network reappears
                        if check_wifi_network(wifi_name) == True and vanished:
                            print("failure during wifi connection detected!")
                            # reconnect
                            os.system("nmcli dev wifi connect " + quote(wifi_name) + " password " + quote(wifi_pass))
                            cli.setup()
                            # ask again for only network parameters
                            nw_dict = {}
                            nname = input("SSID: ")
                            npass = getpass.getpass("KEY: ")
                            nw_dict["name"] = nname
                            nw_dict["key"] = npass
                            json_send(nw_dict, keys) # send new settings
                            # disconnect
                            cli.close() 
                            os.system("nmcli con down id " + quote(wifi_name))
                            os.system("nmcli con delete " + quote(wifi_name))
                            vanished = False


                vanished = False
                print("found")

            finally:
                zeroconf.close()

        # print collected information
        print(found)
        print(list(map(base64.b64encode, keys.values())))
    except:
        traceback.print_exc() # print which error occured

        # inform speaker of error
        cli.send("NOK")
        cli.close()

    
