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

import nacl.bindings as b
import base64

from . import config

# hold private key, do not share outside
priv = None

# generate new keypair
def gen_key():
    global priv

    # generate keys
    priv = b.randombytes(b.crypto_scalarmult_ed25519_BYTES)

    # extract public component
    pubkey = b.crypto_scalarmult_base(priv)

    return base64.b64encode(pubkey).decode("utf-8")

def exchange_key(otherkey):
    global priv

    #decode base64
    other_party_key = base64.b64decode(otherkey);
    shared_key = b.crypto_scalarmult(priv, other_party_key)
    #delete private key
    priv = None
    #return shared key
    return shared_key

def defer_keys(key_material):

    length = config.get_conf("key_len")
    types = config.get_conf("keys")

    keys = {}

    # for all key types set in config derive key
    i = 0
    for t in types:
        t_pad = "{:<8}".format(t.decode('utf-8')).encode('utf-8')
        k = b.crypto_generichash_blake2b_salt_personal(b"", key=key_material, digest_size=32, salt=b'\x00', person=t_pad)
        keys[t] = k

    return keys
