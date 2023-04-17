import subprocess
import os

# say something
def say(text):

    wavfile = None

    # check if there is a prepared .wav for this text
    prepdir = "voice/"+text+".wav"
    if(os.path.exists(prepdir)):
        wavfile = open(prepdir)
    else:
        # if not use picoTTS
        subprocess.run(["pico2wave", "-l", "en-GB", "-w", "/tmp/out.wav", text])
        wavfile = open("/tmp/out.wav")

    subprocess.run(["aplay"], stdin=wavfile)
    
