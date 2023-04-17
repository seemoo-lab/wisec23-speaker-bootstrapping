#!/bin/bash

set -e

#update system
sudo apt update
#sudo apt upgrade -y


#install respeaker drv
#git clone https://github.com/HinTak/seeed-voicecard /tmp/rs
#cd /tmp/rs
#sudo ./install.sh


#install add pkgs
sudo apt install -y git python3-pip python3-prctl libpopt-dev cmake libtool autoconf libportaudio2 avahi-utils avahi-daemon network-manager mplayer libpam-cracklib
pip3 install numpy requests sounddevice zeroconf mycroft-mimic3-tts evdev

# install libquiet

## libcorrect (Git HASH: f5a28c7)
git clone https://github.com/quiet/libcorrect.git /tmp/correct
cd /tmp/correct
cmake .
make -j4
sudo make install
make shim
sudo make install

## libliquid (Git HASH: b64a058)
git clone https://github.com/quiet/quiet-dsp.git -b devel /tmp/libliquid
cd /tmp/libliquid
cmake .
make -j4
sudo make install

## jansson (Git HASH: e23f558)
git clone https://github.com/akheron/jansson.git /tmp/jansson
cd /tmp/jansson

autoreconf -i
./configure
make -j4
sudo make install

## quiet (Git HASH: b64a058)
git clone https://github.com/quiet/quiet.git /tmp/quiet
cd /tmp/quiet

cmake .
make -j4
sudo make install

## quiet.py (Git HASH: 529471c)
git clone https://github.com/xiongyihui/quiet.py.git /tmp/quietpy
cd /tmp/quietpy

pip3 install .

##picoTTS (Git HASH: 21089d2)
git clone https://github.com/naggety/picotts.git /tmp/tts
cd /tmp/tts/pico

./autogen.sh
./configure
make -j4
sudo make install

# libsodium (Git HASH: a1caf97)
# Our clone of pyNACL as we were missing key functions
git clone https://github.com/Markussha/pynacl.git /tmp/nacl
cd /tmp/nacl

pip3 install .


# switch networking to NetworkManager
sudo systemctl disable --now wpa_supplicant
sudo systemctl disable --now dhcpcd

sudo echo "               
denyinterfaces wlan0

" >> /etc/dhcpcd.conf

echo "
[main]
plugins=ifupdown,keyfile
dhcp=internal

[ifupdown]
managed=true
" | sudo tee /etc/NetworkManager/NetworkManager.conf

sudo usermod -aG netdev $USER
sudo sed -i 's/no/yes/g' /var/lib/polkit-1/localauthority/10-vendor.d/org.freedesktop.NetworkManager.pkla
sudo sed -i 's/org.freedesktop.NetworkManager.settings.modify.system/org.freedesktop.NetworkManager.*/g' /var/lib/polkit-1/localauthority/10-vendor.d/org.freedesktop.NetworkManager.pkla

sudo systemctl enable --now NetworkManager

echo "all deps installed!"
sudo ldconfig
