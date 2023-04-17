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

import config

# voice text snippets to use

strings = {
    'en' : {
        'connect_msg_ini' : 'Welcome to See Moo smart speaker. This speaker has not been set up before! Please download the Sonar App and follow the pairing instructions there. This device will now play an acoustic pairing code.',
        'connect_msg_sub' : 'Pairing mode.',
        'cli_name_pre' : 'Device',
        'cli_name_post' : 'wants to pair! Short-press the top of the speaker to deny! Long-press for three seconds to confirm!',
        'wifi_fail' : 'WiFi connection failed! Please retry!',
        'pair_done' : 'Pairing complete.',
        'pair_fail' : 'Pairing failed.',
        'pair_fail_ini': 'Pairing failed. The process will now restart.',
        'confirmed' : 'Confirmed',
        'abort' : 'Cancelled',
        'tutorial_word_selection' : 'The speaker will read out a word. Select this word on your device.'
    }
}

def get_string(name):
    return strings[config.get_conf('lang')][name]
