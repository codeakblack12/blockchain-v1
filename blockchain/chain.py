import threading

from .block import GENESIS, Block

class Blockchain:
    def __init__(self, difficulty: int):
        self.difficulty = difficulty
        self.blocks: list[Block] = [GENESIS]
        self.lock = threading.RLock()

    @property
    def tip(self) -> Block:
        return self.blocks[-1]

    def validate(self, blk: Block) -> tuple[bool, str]:
        recomputed = blk.compute_hash()
        # 1. Hash verification
        if recomputed != blk.hash:
            return False, f"hash mismatch (claimed {blk.hash[:16]}..., recomputed {recomputed[:16]}...)"
        
        # 2. Difficulty verification
        if not blk.hash.startswith("0" * self.difficulty):
           return False, f"insufficient PoW (needs {self.difficulty} leading zeros)"
        tip = self.tip
        if blk.hash == tip.hash:
            return False, f"duplicate of current tip #{tip.index} (already have this block)"

        # 3. Chain continuity
        if blk.prev_hash != tip.hash:
            return False, (f"prev_hash {blk.prev_hash[:16]}... != local tip #{tip.index} "
                           f"hash {tip.hash[:16]}... (conflicting/fork block)")

        # 4. Index sequence
        if blk.index != tip.index + 1:
            return False, f"index {blk.index} != tip index {tip.index} + 1"

        return True, "ok"

    def try_append(self, blk: Block) -> tuple[bool, str]:
        # Append a block to the chain if valid. Returns (ok, reason).
        with self.lock:
            ok, reason = self.validate(blk)
            if ok:
                self.blocks.append(blk)
            return ok, reason

    def to_list(self) -> list[dict]:
        with self.lock:
            return [b.to_dict() for b in self.blocks]
        