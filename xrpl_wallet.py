import ecdsa, hashlib, base58

def generate_wallet():
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()

    seed = b"\x21" + sk.to_string()
    seed_b58 = base58.b58encode_check(seed).decode()

    pub = b"\xED" + vk.to_string()
    addr = hashlib.new('ripemd160', hashlib.sha256(pub).digest()).digest()
    classic = base58.b58encode_check(b"\x00" + addr).decode()

    return {
        "seed": seed_b58,
        "public_key": pub.hex(),
        "classic_address": classic,
    }

# Example:
# print(generate_wallet())
