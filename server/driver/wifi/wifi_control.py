import threading
import os
import time
import subprocess

# start access point
def launch_ap(name, password):
    print(f"nw {name} pass {password}")
    subprocess.run(["nmcli", "dev", "wifi", "hotspot", "con-name", name, "ifname", "wlan0", "ssid", name, "password", password])
    
# stop access point
def stop_ap():
    print("stopping AP")
    connections = subprocess.check_output(["nmcli", "-t", "-f", "name", "connection", "show"]).decode('utf-8').split("\n")
    for con in connections:
        if con != "" and "SEEMOO" in con:
            subprocess.run(["nmcli", "con", "del", con])

# scan and list networks
def get_wifi_networks():
    results = subprocess.check_output(["nmcli", "-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes"])
    results = results.decode("ascii") # needed in python 3
    results = results.replace("\r","")
    ls = results.split("\n")
    return ls

# wait for a network to be scanned
def wait_wifi_network(net_name, timeout):
    start = time.time()
    while True:
        if (time.time() - start > timeout):
            raise Exception("Timeout occured!")
        nw_list = get_wifi_networks()
        if net_name in nw_list:
            break

# remove all NM connections
def purge_nm():
    connections = subprocess.check_output(["nmcli", "-t", "-f", "name", "connection", "show"]).decode('utf-8').split("\n")
    for con in connections:
        if con != "" and "Wired" not in con and "eth" not in con:
            subprocess.run(["nmcli", "con", "del", con])