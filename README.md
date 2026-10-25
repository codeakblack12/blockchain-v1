pip3 install -r requirements.txt

## Running the 3 Nodes
# Terminal 1
python3 main.py --config nodes/node1.json --vanity-prefix PAU --difficulty 6
# Terminal 2
python3 main.py --config nodes/node2.json --vanity-prefix ARD --difficulty 6
# Terminal 3
python3 main.py --config nodes/node3.json --vanity-prefix SHA --difficulty 6