#!/bin/python3

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

import lang
import config
import os
import subprocess
from pathlib import Path

path = "voice"

# check dir exists
if not os.path.exists(path):
    os.makedirs(path)

for i in lang.strings[config.get_conf('lang')].values():
    subprocess.run([str(Path.home()) + "/.local/bin/mimic3", i], stdout=open(os.path.join(path, i + ".wav"), "w"))