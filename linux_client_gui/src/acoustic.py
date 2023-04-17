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

import argparse
import queue
import sys

import numpy as np
import sounddevice as sd
from quiet import Decoder
import os

# queue holding audio data
q = queue.Queue()

# callback storing read audio data to queue
def audio_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(indata[::, [0]])

# quiet objects
print(os.path.dirname(__file__))
decoder = Decoder(profile_name='custom', profiles="/app/share/SpeakerServer/linux_client_gui/quiet.json")
stream = sd.InputStream(
    channels=1,
    samplerate=44100, callback=audio_callback)

def device_name():
    return sd.query_devices(device=sd.default.device[0])["name"]

# start decoding
def decode_start():
    stream.start()

# get data from queue and evaluate
def decode_poll():
    audio = q.get()
    audio = np.fromstring(audio, dtype='float32')
    #print(audio)
    code = decoder.decode(audio)
    if code is not None:
        stream.stop() # stop decoding
        print(code.tostring().decode('utf-8', 'ignore'))
        return code.tostring().decode('utf-8', 'ignore')
    return None

# stop decoding
def decode_stop():
    stream.stop()

# blocking decode
def decode():
    decode_start()
    while True:
        decode_poll()



