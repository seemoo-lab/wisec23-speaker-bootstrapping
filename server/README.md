# Server

This folder contains the Server implementation.

## Building

The server is a raw python program. The server is meant for execution on Raspberry Pi OS. We used Raspberry Pi OS Bullseye (04.04.2022) with Kernel 5.15.

### Installing necessary dependencies

install.sh installs all dependencies from source or via apt/pip if available. The ReSpeaker driver necessary for audio in/out will not be built from by the script as the FreeSpeaker hardware requires a patched driver. The installation routine for the default driver is available as a comment in this script.
The script will print "all deps installed" if it succeeds.

A fresh Raspberry Pi OS installation requires the following steps:

- Install FreeSpeaker hardware drivers (Button, Speakers)

- Execute ./install.sh

## Running the server

The main entrypoint is server_threaded.py.

Python 3.10 was used during development. As the FreeSpeaker requires GPIO pins to be set up, runner.sh prepares the GPIO and starts the server.

## Fancier voices

By default, picoTTS is used for speech output. Better-sounding voice engines are available, but at least the ones we tried require too much computation time on the Pi.

prepare_hq_voice.py can be executed to prepare static text strings defined in lang.py as .wav files. Mimic3 is used as the voice engine by this script. The TTS driver checks if a string is available as .wav and plays it. If unavailable, picoTTS is invoked.
