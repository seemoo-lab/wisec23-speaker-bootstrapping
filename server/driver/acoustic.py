from quiet import Encoder
import sounddevice as sd
import numpy as np
from functools import reduce

import subprocess
import signal
import prctl

CHANNELS = 1
RATE = 44100
CHUNK = 16384*6

player = None

# transmit an acoustic message
# loop: play in loop
# stop_prev: kill previous xmission

def transmit_message(msg, loop=False, stop_prev=True):
    global player

    # quiet encoder
    # always create new encoder to avoid noise in output
    e = Encoder(profile_name='custom', profiles="quiet_profiles.json")

    # kill previous messages
    if stop_prev:
        sd.stop()
    
    # use quiet and concat blocks
    chunks = e.encode(msg, chunk_size=CHUNK)
    plain_msg = reduce(lambda a,b : np.concatenate((a,b)), chunks)

    # play message
    sd.play(plain_msg, RATE, loop=loop)
    # play overlay
    player = subprocess.Popen(["mplayer", "-af", "volume=-20", "-loop", "0", "audio/pairing_overlay.mp3"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL))


# stop xmit
def stop_transmit():
    global player

    sd.stop()
    if (player != None):
        player.terminate()
        player = None
