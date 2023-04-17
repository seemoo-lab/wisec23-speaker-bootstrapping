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

from . import acoustic as ac
from . import config
import os
import requests
from . import ecdh as dh
from . import sock_cli as cli
from . import database
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
import threading

from gi.repository import Notify

# file used to generate verification words
word_file = "/app/share/SpeakerServer/linux_client_gui/wordfile.txt"

# helper function to list wifi networks with NMcli
def get_wifi_networks():
    """! Scans wifi networks and returns them.

    @return  List of SSIDs.
    """

    results = subprocess.check_output(["flatpak-spawn", "--host", "nmcli", "-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes"])
    results = results.decode("ascii") # needed in python 3
    results = results.replace("\r","")
    ls = results.split("\n")
    return ls

# waits with timeout until a wifi network becomes available
def wait_wifi_network(net_name, timeout):
    """! Block until a network appears.

    @param net_name   SSID to wait for.
    @param timeout    Timeout in seconds.
    """

    start = time.time()
    while True:
        if (time.time() - start > timeout):
            raise Exception("Timeout occured!")
        nw_list = get_wifi_networks()
        if net_name in nw_list:
            break

# check if a network is available
def check_wifi_network(net_name):
    """! Check if a wifi network is available
    @param net_name   SSID to check.
    @return  Boolean representing result.
    """

    nw_list = get_wifi_networks()
    if net_name in nw_list:
        return True
    return False

found = None

# send a dictionary as JSON and encrypted+authenticated to the server
def json_send(nw_dict, keys):
    """! Encrypt a dictionary and send it.
    @param nw_dict   Dictionary to encrypt.
    @param keys   List of keys.
    """

    json_nw = json.dumps(nw_dict)

    nonce = b.randombytes(b.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
    ciphertext = b.crypto_aead_xchacha20poly1305_ietf_encrypt(str(json_nw).encode("utf-8"), b"", nonce, keys[b"encrypt"])

    json_k = [ 'nonce', 'ciphertext' ]
    json_v = [ base64.b64encode(x).decode('utf-8') for x in [nonce, ciphertext] ]
    nwconfig_send = json.dumps(dict(zip(json_k, json_v)))

    cli.send(nwconfig_send)

# bytestring to base64 string
def b2b64str(bytestring_to_convert):
    """! Convert byte array to base64 string.
    @param bytestring_to_convert   bytearray.
    @return  string.
    """
    return base64.b64encode(bytestring_to_convert).decode("utf-8")

# pairing function
def pair(initial, window, ip, name):
    """! Check if a wifi network is available
    @param initial  Boolean that is true if this is an initial pairing.
    @param window  UI window governing this pairing.
    @param ip  IP of server.
    @param name  Name of server.
    @return  Established keys.
    """

    # give window time to start
    while not window.is_active():
        pass

    if not initial:
        window.show_icon_text("user-status-pending-symbolic", "Reaching out to your speaker...")

        cli.setup(ip)
        repl = cli.recv()

        if repl == "KO":
            window.show_icon_text("action-unavailable-symbolic", "Pairing is not allowed!")
            cli.close()
            return
        if repl == "EX":
            window.show_icon_text("emblem-default-symbolic", "Allow pairing from a second client!")
            print("Make sure allow pair")

            while True:
                if cli.check_data_avail():
                    print("avail")
                    break
                time.sleep(0.2)
                try:
                    window.check()
                except Exception as e:
                    print("closing")
                    cli.close()
                    raise e

            grant = cli.recv()

    try:
        # get current wifi pass and ssid
        nwinfo = subprocess.check_output(["flatpak-spawn", "--host", "nmcli", "dev", "wifi", "show-password"])
        nwinfo_line = nwinfo.decode('utf-8').split('\n')
        ssid_read = nwinfo_line[0].split(': ')[1]
        psk_read = nwinfo_line[2].split(': ')[1]
        window.set_wifi(ssid_read, psk_read)

        window.show_icon_text("audio-input-microphone-symbolic", "Listening for your speaker...")
        # generate a client UUID for use with this speaker
        # TODO: use sqlite like in server
        uuid = database.DB().get_uuid()

        print("scanning pairing code and looking for zeroconf devices if any")

        # start decoding audio message
        ac.decode_start()

        # holds received audio msg
        str_msg = None
        # for network pairing, we need to scan another code
        ac.decode_start()
        while True:
            str_msg = ac.decode_poll()
            window.check()
            window.show_icon_text("audio-input-microphone-symbolic", "Listening for your speaker on: "+ac.device_name())
            # make sure type is networked
            if str_msg != None:
                break

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

        window.check()
        if (initial):
            window.show_icon_text("system-search-symbolic", "Looking for your speaker...")
            print("scanning networks:")
            # look for the AP created by the speaker
            # timeout after 60 seconds
            # TODO: move timeout to config
            wait_wifi_network(wifi_name, 60)
            window.check()

            window.show_icon_text("network-cellular-connected-symbolic", "Connecting to your speaker...")
            print("connecting via NM:")
            # connect to wifi
            # TODO: move to subprocess
            os.system("flatpak-spawn --host nmcli dev wifi connect " + quote(wifi_name) + " password " + quote(wifi_pass))
            window.check()

        window.show_icon_text("network-transmit-receive-symbolic", "Talking to your speaker...")

        client_pubkey = dh.gen_key() # generate ecdh keypair
        client_uuid_str = str(uuid) # convert uuid to network-transferrable representation

        # exchange ECDH keys
        if initial:
            cli.setup() # connect to default IP set by initial access point

        cli.send(client_uuid_str) # send client UUID to speaker
        cli.send(client_pubkey) # send client pubkey to speaker

        window.check()

        # get UUID and ECDH from speaker
        speaker_uuid_plain = cli.recv()
        speaker_key = cli.recv()

        window.check()

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
        if initial:
            msg = b.crypto_auth((client_uuid_str + client_pubkey + socket.gethostname()).encode("utf-8"), keys[b'sign'])
            #msg = digest(keys[b'sign'], (client_uuid_b64str + client_publey + socket.gethostname()).encode("utf-8"), "sha256")
        else:
            # here the client also proves that he received the secret in the audio message fromthe speaker and must therefore be close
            msg = b.crypto_auth((client_uuid_str + client_pubkey + socket.gethostname() + n_secret).encode("utf-8"), keys[b'sign'])
            #msg = digest(keys[b'sign'], (client_uuid_b64str + client_publey + socket.gethostname() + n_secret).encode("utf-8"), "sha256")

        cli.send(b2b64str(msg))

        window.check()

        window.show_icon_text("daytime-sunset-symbolic", "Please confirm pairing by long-pressing the top of ypur speaker")

        reply = cli.recv() #server may abort here if hash is broken (abort implemented in recv function)
        window.check()

        # Loud&clear style verification
        # pick words at random from a file
        # rng is initialized with verify key
        if True:
            # file is closed as object directly falls out of context
            words = open(word_file).read().splitlines()
            sel = b.randombytes_buf_deterministic(4, keys[b'verify'])
            result = 0
            for i in range(4):
                result = int(result) | ( (int(sel[i]) & 0xff ) << (8 * i) )
            result = result % len(words)
            chosen_words = [words[result],]

            # draw words
            for i in range(4):
                sel = random.randrange(0, len(words)-1)
                chosen_words.append(words[sel])
            # show and ask user
            print(chosen_words)
            word_repl = window.get_word_select(chosen_words)
            window.check()
            if not word_repl:
                cli.send('NOK')
                raise Exception("Error during verification")
            cli.send("OK")

        # Send settings struct to speaker
        # TODO: Decouple network config and verification settings/speaker naming to simplify code here
        # TODO: Move strings to config
        nw_dict = {}
        spk_name = name
        if initial:
            # collect and store user input
            print("Network setup requested! (WPA2 only currently!)")
            hostn = window.get_spkname()
            spk_name = hostn
            nname, npass = window.get_wifi_settings()
            window.check()
            nw_dict["name"] = nname
            nw_dict["key"] = npass
            nw_dict["host"] = hostn

            # send settings as encrypted JSON
            json_send(nw_dict, keys)


        time.sleep(1)
        cli.close() # done talking to speaker


        # on first setup, speaker must connect to wifi
        if initial:
            # delete and deassociate connection to speaker
            print("disconnecting")
            os.system("flatpak-spawn --host nmcli con down id " + quote(wifi_name))
            os.system("flatpak-spawn --host nmcli con delete " + quote(wifi_name))

            window.show_icon_text("network-wireless-signal-good-symbolic", "Connecting your speaker to your network...")
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
            window.check()

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
                    window.check()
                    if (reply == "NW"):
                        # if network disappears we are ready to wait for reappearing
                        if check_wifi_network(wifi_name) == False and vanished == False:
                            vanished = True
                        # if network reappears
                        window.check()
                        if check_wifi_network(wifi_name) == True and vanished:
                            print("failure during wifi connection detected!")
                            # reconnect
                            os.system("flatpak-spawn --host nmcli dev wifi connect " + quote(wifi_name) + " password " + quote(wifi_pass))
                            cli.setup()
                            # ask again for only network parameters
                            nw_dict = {}
                            nname, npass = window.get_wifi_settings()
                            #nname = input("SSID: ")
                            #npass = getpass.getpass("KEY: ")
                            nw_dict["name"] = nname
                            nw_dict["key"] = npass
                            json_send(nw_dict, keys) # send new settings
                            # disconnect
                            cli.close()
                            os.system("flatpak-spawn --host nmcli con down id " + quote(wifi_name))
                            os.system("flatpak-spawn --host nmcli con delete " + quote(wifi_name))
                            vanished = False


                vanished = False
                print("found")

                # print collected information
                print(found)
                print(list(map(base64.b64encode, keys.values())))

            finally:
                zeroconf.close()

        database.DB().insert_speaker(speaker_uuid_plain, spk_name, base64.b64encode(keys[b"encrypt"]), base64.b64encode(keys[b"sign"]), base64.b64encode(keys[b"verify"]))

        Notify.Notification.new("Pairing success!").show()
        window.show_icon_text("weather-clear-symbolic", "Pairing successful!")



    except:
        traceback.print_exc() # print which error occured

        try:
            # inform speaker of error
            cli.send("NOK")
            cli.close()
        except:
            pass

        try:
            window.check()
            window.show_icon_text("computer-fail-symbolic", "Pairing failed!")
            Notify.Notification.new("Pairing failed!").show()
        except:
            pass

    finally:
        ac.decode_stop()

def run_pair(initial, window, ip, name):
    """! Start pairing thread
    @param initial  Boolean that is true if this is an initial pairing.
    @param window  UI window governing this pairing.
    @param ip  IP of server.
    @param name  Name of server.
    """

    pth = threading.Thread(target=pair, args=(initial,window,ip,name))
    pth.daemon = True
    pth.start()

def error():
    cli.send('NOK')
