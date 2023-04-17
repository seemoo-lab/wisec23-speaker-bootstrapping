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

from . import database as db
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import socket
from gi.repository import Gtk, GLib

zc_speakers = []
treelist = None
window = None

class NewSpeakerListener(ServiceListener):
    # necessary to avoid exceptions
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        global zc_speakers

        try:
            # store info about found speaker
            info = zc.get_service_info(type_, name)
            uuid = name.split('.')[0]

            for s in zc_speakers:
                if s[1] == uuid:
                    zc_speakers.remove(s)
                    break
            GLib.idle_add(update)
        except:
            pass

    # wait for correct speaker to get found
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        global zc_speakers

        try:
            # store info about found speaker
            info = zc.get_service_info(type_, name)
            ip = socket.inet_ntoa(info.addresses[0])
            item = (ip, info.properties[b"uuid"].decode("utf-8"), info.properties[b"name"].decode("utf-8"))
            zc_speakers.append(item)

            GLib.idle_add(update)
        except:
            pass

def start(tl, win):
    global treelist
    global window

    treelist = tl
    window = win
    #enable browsing
    zeroconf = Zeroconf()
    listener = NewSpeakerListener()
    browser = ServiceBrowser(zeroconf, "_SEEMOOSPEAKER._tcp.local.", listener)

def update():
    global zc_speakers
    global treelist
    global window


    treelist.clear()

    dbcon = db.DB() # get access to DB in this thread
    db_speakers = dbcon.get_speakers() # lists uuid, name

    zc_spk_loc = zc_speakers.copy()

    for spk in db_speakers:

        avail = False
        zc_line = None

        #look in zc_spk_loc
        for s in zc_spk_loc: # if found
            if s[1] == spk[0]:
                # delete from zc list and store info
                avail = True
                zc_line = s
                zc_spk_loc.remove(s)

        # add to list
        if avail:
            treelist.append(["changes-prevent-symbolic",
                         f"{spk[1]}\n{spk[0]} | {zc_line[0]}", "user-trash-symbolic"])
        else:
            treelist.append(["preferences-desktop-screensaver-symbolic",
                         f"{spk[1]}\n{spk[0]} | -", "user-trash-symbolic"])

    print(f"len zc: {len(zc_spk_loc)}")
    for s in zc_spk_loc:
        treelist.append(["changes-allow-symbolic",
                     f"{s[2]}\n{s[1]} | {s[0]}", ""])

    GLib.idle_add(window.stackupd)



    
