import argparse
import json
import sys

from blockchain.node import Node
from blockchain.wallet import load_or_create_identity, matches_prefix, normalize_prefix

HELP = """Commands:
  msg <text>   add a pending message (local to this node)
  mine         mine one block with pending messages, then broadcast
  chain        print the local chain
  status       print height / tip / pending messages
  peers        list configured peers
  help         show this help
  exit         stop the node"""

def print_chain(node: Node):
    for b in node.chain.blocks:
        print(f"  #{b.index} hash={b.hash[:20]}... prev={b.prev_hash[:12]}... "
              f"nonce={b.nonce} miner={b.miner_address} data={b.data}")
        
def main():
    ap = argparse.ArgumentParser(description="ECE 496C/519C Assignment 1 node")
    ap.add_argument("--config", required=True, help="node config JSON (node1.json ...)")
    ap.add_argument("--vanity-prefix", required=True, help="first 3 letters of your name")
    ap.add_argument("--difficulty", type=int, default=4, help="leading hex zeros (default 4)")
    ap.add_argument("--keypair", default="keypair.json", help="vanity keypair file")
    args = ap.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    # ---------- Part 1: identity
    prefix = normalize_prefix(args.vanity_prefix)
    identity = load_or_create_identity(prefix, args.keypair)
    addr = identity["address"]
    print(f"[+] Public Address : {addr}")
    if matches_prefix(addr, prefix):
        print(f"[+] Prefix Status  : MATCH FOUND (\"{addr[1:4]}\" matches \"{prefix}\" case-insensitive)")
    else:
        sys.exit("[-] Prefix Status  : NO MATCH")
    print("[+] Node Identity initialized successfully.")

    # ---------- Part 2: node
    node = Node(config, identity, args.difficulty)

    try:
        httpd = node.serve()
    except OSError as e:
        sys.exit(f"[-] Could not bind port {config['port']}: {e}")
    print(f"[+] Difficulty: {args.difficulty}  |  type 'help' for commands")

    prompt = f"{node.node_id}> "
    while True:
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        cmd, _, rest = line.partition(" ")
        cmd = cmd.lower()
        if cmd == "msg":
            node.add_message(rest) if rest.strip() else print("usage: msg <text>")
        elif cmd == "mine":
            node.mine()
        elif cmd == "chain":
            print_chain(node)
        elif cmd == "status":
            print(json.dumps(node.status(), indent=2))
        elif cmd == "peers":
            print("\n".join(node.peers))
        elif cmd == "help":
            print(HELP)
        elif cmd in ("exit", "quit"):
            break
        else:
            print(f"unknown command {cmd!r} - type 'help'")
    httpd.shutdown()
    print("[+] Node stopped.")

if __name__ == "__main__":
    main()