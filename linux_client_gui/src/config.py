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


# All config options are held here

conf = {
    'lang' : 'en',
    'network_prefix' : 'SEEMOO_SPEAKER_',
    'network_randoms' : 4,
    'pin_randoms' : 8,
    'log_dir' : '/var/log/spksrv',
    'key_len' : 32,
    'keys' : [b"encrypt", b"sign", b"verify"],
}

# helper to extract items
def get_conf(name):
    return conf[name]
