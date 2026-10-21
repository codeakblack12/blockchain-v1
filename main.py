import argparse
import json
import sys
from blockchain.wallet import load_or_create_identity, matches_prefix, normalize_prefix

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

if __name__ == "__main__":
    main()