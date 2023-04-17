import subprocess
import prctl
import signal
import driver.database as db
import os
import config

# service announcement

p = None

# disannounce service
def disannounce():
    global p
    if(p != None):
        p.kill()
        p = None

# announce service  
def announce():
    global p

    dbcon = db.DB()

    disannounce()
    if(dbcon.read_setting("name") != None):
        print("announce service")
        p = subprocess.Popen(["avahi-publish-service",  str(dbcon.get_uuid()), "_SEEMOOSPEAKER._tcp", str(config.get_conf("example_port")), "uuid="+str(dbcon.get_uuid()), "name="+dbcon.read_setting("name")[0]], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL))
