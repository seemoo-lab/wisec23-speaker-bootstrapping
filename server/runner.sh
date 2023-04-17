#!/bin/bash
# This is only required on the freespeaker and enables the speaker
# TODO Is it possible to tell the driver to use this pin to activate when the device is used?
echo 17 | sudo tee /sys/class/gpio/export
echo out | sudo tee /sys/class/gpio/gpio17/direction
echo 1 | sudo tee /sys/class/gpio/gpio17/value


python3 server_threaded.py
