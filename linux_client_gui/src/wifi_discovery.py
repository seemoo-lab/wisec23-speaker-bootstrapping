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

from gi.repository import GLib
import threading
import subprocess


# create thread
def start(button):
    pth = threading.Thread(target=check_wifi, args=(button,))
    pth.daemon = True
    pth.start()

# check if wifi is present and enable / disable button
def check_wifi(button):
    while True:
        # scan for networks
        results = subprocess.check_output(["flatpak-spawn", "--host", "nmcli", "-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes"]).decode("utf-8").replace("\r","")
        ls = results.split("\n")
        for nw in ls:
            if "SEEMOO_SPEAKER" in nw:
                GLib.idle_add(button.set_sensitive, True)
                GLib.idle_add(button.set_tooltip_text,"Press to pair new speaker")
                break
            else:
                GLib.idle_add(button.set_sensitive, False)
                GLib.idle_add(button.set_tooltip_text,"No new speaker nearby")


