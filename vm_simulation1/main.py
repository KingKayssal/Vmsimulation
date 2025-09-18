#python main.py --controller --host 127.0.0.1 --port 6000
#python main.py --node --id vm1 --controller-host 127.0.0.1 --controller-port 6000 --port 5001

print("[DEBUG] main.py started")
import argparse
import threading
from controller import serve_controller, start_dashboard
from node import run_node

parser = argparse.ArgumentParser()
parser.add_argument("--controller", action="store_true")
parser.add_argument("--node", action="store_true")
parser.add_argument("--id", type=str, help="Node ID")
parser.add_argument("--controller-host", type=str, default="127.0.0.1")
parser.add_argument("--controller-port", type=int, default=6000)
parser.add_argument("--host", type=str, default="127.0.0.1")
parser.add_argument("--port", type=int, default=5000)
args = parser.parse_args()

if args.controller:
    print("[DEBUG] args.controller is True")
    start_dashboard()
    print("[Controller] Web dashboard is running at http://127.0.0.1:8080/ (open in your browser)")
    serve_controller(args.host, args.port)
elif args.node:
    print("[DEBUG] args.node is True")
    run_node(args.id, args.controller_host, args.controller_port, args.host, args.port)
