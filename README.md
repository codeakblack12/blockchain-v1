pip3 install -r requirements.txt

## Running the 3 Nodes
# Terminal 1
python3 main.py --config node1.json --vanity-prefix PAU --difficulty 4
# Terminal 2
python3 main.py --config node2.json --vanity-prefix PAU --difficulty 4
# Terminal 3
python3 main.py --config node3.json --vanity-prefix PAU --difficulty 4