import base64
import nacl.bindings as b
import config

priv = None

# generate random key
def gen_key():
    global priv

    # generate keys
    priv = b.randombytes(b.crypto_scalarmult_ed25519_BYTES)

    # extract public component
    pubkey = b.crypto_scalarmult_base(priv)

    return base64.b64encode(pubkey).decode("utf-8")

# use provided pubkey and internal privkey to derive IKM
def exchange_key(otherkey):
    global priv

    #decode base64
    other_party_key = base64.b64decode(otherkey);
    shared_key = b.crypto_scalarmult(priv, other_party_key)
    #delete private key
    priv = None
    #return shared key
    return shared_key

# use IKM to derive further keys
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
