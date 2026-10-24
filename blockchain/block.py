import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

class Block:
    index: int
    prev_hash: str
    timestamp: str
    data: list = field(default_factory=list)
    nonce: int = 0
    miner_address: str = ""
    hash: str = ""

    # Hashing the block header (index, timestamp, prev_hash, data, nonce, miner_address) using SHA256
    # ============================================================================
    def header_string(self, nonce: int | None = None) -> str:
        n = self.nonce if nonce is None else nonce
        data_json = json.dumps(self.data, separators=(",", ":"), ensure_ascii=False)
        return f"{self.index}|{self.timestamp}|{self.prev_hash}|{data_json}|{n}|{self.miner_address}"

    def compute_hash(self, nonce: int | None = None) -> str:
        return hashlib.sha256(self.header_string(nonce).encode("utf-8")).hexdigest()

    # Converting the block to a dictionary
    # ============================================================================
    def to_dict(self) -> dict:
        return asdict(self)
    
    def from_dict(cls, d: dict) -> "Block":
        return cls(
            index=int(d["index"]),
            prev_hash=str(d["prev_hash"]),
            timestamp=str(d["timestamp"]),
            data=list(d["data"]),
            nonce=int(d["nonce"]),
            miner_address=str(d["miner_address"]),
            hash=str(d["hash"]),
        )

# Creating the genesis block
# ============================================================================
def make_genesis() -> Block:
    g = Block(
        index=0,
        prev_hash="0000000000000000000000000000000000000000000000000000000000000000",
        timestamp="2026-01-01T00:00:00Z",
        nonce=0,
        miner_address="GENESIS",
        data=["Genesis Block"],
    )
    g.hash = g.compute_hash()  # trusted; not required to meet difficulty
    return g


GENESIS = make_genesis()

def utc_now() -> str:
    # Returns the current UTC time in ISO 8601 format with milliseconds precision and a "Z" suffix.
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

# PoW
# ============================================================================
def mine_block(prev: Block, data: list, miner_address: str, difficulty: int,
               log=print, log_every: int = 250_000) -> Block:
    target = "0" * difficulty
    blk = Block(index=prev.index + 1, prev_hash=prev.hash, timestamp=utc_now(),
                data=list(data), nonce=0, miner_address=miner_address)
    log(f"[+] Block #{blk.index} Target Difficulty: {difficulty} leading zeros (\"{target}...\")")
    nonce = 0
    while True:
        h = blk.compute_hash(nonce)
        if nonce == 0 or nonce % log_every == 0:
            log(f"[+] Nonce: {nonce:<8} -> Hash: {h}")
        if h.startswith(target):
            break
        nonce += 1
    blk.nonce, blk.hash = nonce, h
    log(f"[+] Nonce: {nonce:<8} -> Hash: {h}")
    log(f"[+] Block #{blk.index} Mined! Nonce: {nonce}")
    log(f"[+] Block Hash: {h}")
    log(f"[+] Miner: {miner_address}")
    return blk