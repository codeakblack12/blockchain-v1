import hashlib
import json
import multiprocessing as mp
import os
import time

from Crypto.Hash import RIPEMD160
from ecdsa import SECP256k1, SigningKey

B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" #Omit 0, O, I, l
MAINNET_VERSION = b"\x00"

# ============================================================================

def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def ripemd160(b: bytes) -> bytes:
    return RIPEMD160.new(b).digest()

# This treats the byte string as one big integer and repeatedly divides by 58 (length of B58_ALPHABET) 
# the remainder at each step picks a character from the alphabet
def base58_encode(raw: bytes) -> str:
    num = int.from_bytes(raw, "big")
    out = ""
    while num > 0:
        num, rem = divmod(num, len(B58_ALPHABET))
        out = B58_ALPHABET[rem] + out
    # every leading 0x00 byte is encoded as a leading '1'
    pad = len(raw) - len(raw.lstrip(MAINNET_VERSION))
    return "1" * pad + out

# ============================================================================
def compressed_pubkey(sk: SigningKey) -> bytes:
    return sk.get_verifying_key().to_string("compressed")  # 33 bytes (02/03 || X)

def pubkey_to_address(pubkey: bytes) -> str:
    pubkey_hash = ripemd160(sha256(pubkey))            # HASH160
    versioned = MAINNET_VERSION + pubkey_hash          # 0x00 prefix
    checksum = sha256(sha256(versioned))[:4]           # double-SHA256
    return base58_encode(versioned + checksum)         # Base58Check

def generate_keypair():
    sk = SigningKey.generate(curve=SECP256k1)
    pub = compressed_pubkey(sk)
    return sk.to_string().hex(), pub.hex(), pubkey_to_address(pub)

# ============================================================================
def normalize_prefix(prefix: str) -> str:
    import unicodedata

    p = unicodedata.normalize("NFKD", prefix)
    p = "".join(c for c in p if c.isascii() and c.isalpha()).upper()
    if len(p) < 3:
        raise ValueError("Vanity prefix must contain at least 3 letters (A-Z)")
    return p[:3]


def matches_prefix(address: str, prefix: str) -> bool:
    # Characters 2-4 (address[1:4]) must equal prefix, case-insensitive.
    return address.startswith("1") and address[1:4].upper() == prefix.upper()


def _worker(prefix, found, counter):
    local = 0
    while not found.is_set():
        priv, pub, addr = generate_keypair()
        local += 1
        if local % 500 == 0:
            with counter.get_lock():
                counter.value += 500
        if matches_prefix(addr, prefix):
            found.set()
            return {"private_key": priv, "public_key": pub, "address": addr}
    return None

def search_vanity(prefix: str, workers: int | None = None) -> dict:
    prefix = normalize_prefix(prefix)
    workers = workers or os.cpu_count() or 1
    print(f"[+] Searching for vanity address 1{prefix}... using {workers} process(es)")
    start = time.time()
    with mp.Manager() as mgr:
        found = mgr.Event()
        counter = mp.Value("L", 0)
        with mp.Pool(workers, initializer=_init_counter, initargs=(counter,)) as pool:
            results = [pool.apply_async(_worker_entry, (prefix, found)) for _ in range(workers)]
            while not found.is_set():
                time.sleep(1)
                print(f"    ...{counter.value:,} keys tried ({time.time() - start:.0f}s)", end="\r")
            hit = next(r.get() for r in results if r.get() is not None)
    print(f"\n[+] Match found in {time.time() - start:.1f}s")
    return hit


_COUNTER = None

def _init_counter(c):
    global _COUNTER
    _COUNTER = c


def _worker_entry(prefix, found):
    return _worker(prefix, found, _COUNTER)


# ============================================================================
def verify_keypair(kp: dict) -> bool:
    """Re-derive pubkey + address from the private key to prove the file is consistent."""
    sk = SigningKey.from_string(bytes.fromhex(kp["private_key"]), curve=SECP256k1)
    pub = compressed_pubkey(sk)
    return pub.hex() == kp["public_key"] and pubkey_to_address(pub) == kp["address"]


def load_or_create_identity(prefix: str, path: str = "keypair.json") -> dict:
    prefix = normalize_prefix(prefix)
    if os.path.exists(path):
        print(f"[+] Loading keypair from {path}...", end=" ")
        with open(path) as f:
            kp = json.load(f)
        if verify_keypair(kp) and matches_prefix(kp["address"], prefix):
            print("(Found existing match)")
            return kp
        print("(Stored key invalid or prefix mismatch - regenerating)")
    kp = search_vanity(prefix)
    kp["prefix"] = prefix
    with open(path, "w") as f:
        json.dump(kp, f, indent=2)
    print(f"[+] Saved keypair to {path}")
    return kp