import json
import queue
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .block import Block, mine_block
from .chain import Blockchain

class Node:
    def __init__(self, config: dict, identity: dict, difficulty: int):
        self.node_id = config["node_id"]
        self.port = int(config["port"])
        self.peers = list(config.get("peers", []))
        self.address = identity["address"]
        self.chain = Blockchain(difficulty)
        self.pending: list[str] = []
        self.pending_lock = threading.Lock()
        self.inbox: "queue.Queue[tuple[Block, str]]" = queue.Queue()
        self.mining = threading.Event()
        self.print_lock = threading.Lock()

    # Logging
    # ============================================================================
    def log(self, msg: str):
        with self.print_lock:
            print(msg, flush=True)

    # Messages
    def add_message(self, text: str):
        with self.pending_lock:
            self.pending.append(text)
            n = len(self.pending)
        self.log(f"[+] Message queued ({n} pending): {text!r}")

    # Mining
    # ============================================================================
    def mine(self) -> Block | None:
        if self.mining.is_set():
            self.log("[!] Already mining - request ignored")
            return None
        self.mining.set()
        try:
            self.log(f"[+] Triggering Mining Cycle on {self.node_id}...")
            with self.pending_lock:
                data, self.pending = self.pending, []
            # The chain lock is held for the whole PoW search: blocks that arrive
            # from peers meanwhile wait in the inbox. This is what makes the
            # First-Valid-Block-Wins fork reproducible in the demo.
            with self.chain.lock:
                blk = mine_block(self.chain.tip, data, self.address,
                                 self.chain.difficulty, log=self.log)
                ok, reason = self.chain.try_append(blk)   # local chain first
            if not ok:
                self.log(f"[!] Own block rejected locally: {reason}")
                return None
            self.log(f"[+] Block #{blk.index} appended to local chain (height {blk.index})")
            self.broadcast(blk)
            return blk
        finally:
            self.mining.clear()

    # Networking
    # ============================================================================
    def broadcast(self, blk: Block):
        body = json.dumps({"block": blk.to_dict(), "from": self.node_id}).encode()

        def send(peer):
            try:
                req = urllib.request.Request(f"{peer}/block", data=body, method="POST",
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=3) as r:
                    self.log(f"[+] Broadcast Block #{blk.index} -> {peer} (HTTP {r.status})")
            except (urllib.error.URLError, OSError) as e:
                self.log(f"[WARN] Peer {peer} unreachable ({getattr(e, 'reason', e)}) - continuing")

        threads = [threading.Thread(target=send, args=(p,), daemon=True) for p in self.peers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def _inbox_worker(self):
        # Processes received blocks one at a time (waits while we are mining).
        while True:
            blk, sender = self.inbox.get()
            self.log(f"\n[+] Received Block #{blk.index} from {sender} "
                     f"(miner {blk.miner_address}, hash {blk.hash[:20]}...)")
            ok, reason = self.chain.try_append(blk)
            if ok:
                self.log("    [OK] 1. hash  2. difficulty  3. continuity  4. index -> all checks passed")
                self.log(f"    [OK] Block #{blk.index} appended. Height = {self.chain.tip.index}")
            else:
                self.log(f"    [REJECTED] {reason}")

    def serve(self):
        node = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence default access log
                pass

            def _send(self, code, obj):
                payload = json.dumps(obj, indent=2).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _body(self):
                n = int(self.headers.get("Content-Length", 0))
                return json.loads(self.rfile.read(n) or b"{}")

            def do_GET(self):
                if self.path == "/chain":
                    self._send(200, node.chain.to_list())
                elif self.path == "/status":
                    self._send(200, node.status())
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                try:
                    body = self._body()
                except json.JSONDecodeError:
                    return self._send(400, {"error": "invalid JSON"})
                if self.path == "/block":
                    try:
                        blk = Block.from_dict(body["block"])
                    except (KeyError, TypeError, ValueError) as e:
                        return self._send(400, {"error": f"malformed block: {e}"})
                    node.inbox.put((blk, body.get("from", self.client_address[0])))
                    self._send(202, {"status": "queued for validation"})
                elif self.path == "/message":
                    text = str(body.get("text", "")).strip()
                    if not text:
                        return self._send(400, {"error": "text required"})
                    node.add_message(text)
                    self._send(200, {"pending": len(node.pending)})
                elif self.path == "/mine":
                    if node.mining.is_set():
                        return self._send(409, {"error": "already mining"})
                    threading.Thread(target=node.mine, daemon=True).start()
                    self._send(202, {"status": "mining started"})
                else:
                    self._send(404, {"error": "not found"})


        httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        threading.Thread(target=self._inbox_worker, daemon=True).start()
        self.log(f"[+] {self.node_id} listening on http://127.0.0.1:{self.port}")
        self.log(f"[+] Peers: {', '.join(self.peers) or '(none)'}")
        return httpd

    def status(self) -> dict:
        tip = self.chain.tip
        return {"node_id": self.node_id, "address": self.address,
                "difficulty": self.chain.difficulty, "height": tip.index,
                "tip_hash": tip.hash, "pending": list(self.pending),
                "mining": self.mining.is_set()}