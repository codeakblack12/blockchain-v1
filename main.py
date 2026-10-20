import argparse
import json
import sys

def main():
    ap = argparse.ArgumentParser(description="ECE 496C/519C Assignment 1 node")
    ap.add_argument("--config", required=True, help="node config JSON (node1.json ...)")
    ap.add_argument("--vanity-prefix", required=True, help="first 3 letters of your name")
    ap.add_argument("--puzzle", type=int, default=4, help="leading hex zeros (default 4)")
    ap.add_argument("--keypair", default="keypair.json", help="vanity keypair file")
    args = ap.parse_args()

    with open(args.config) as f:
        config = json.load(f)