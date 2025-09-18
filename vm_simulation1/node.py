import os
import sys
import time
import threading
import random
from datetime import datetime
import grpc
from concurrent import futures
from proto import storage_pb2, storage_pb2_grpc

# Optional: colorized output
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Dummy:
        def __getattr__(self, name): return ''
    Fore = Style = Dummy()


# ---------------- gRPC File Service (for peer-to-peer downloads) ----------------
class NodeFileService(storage_pb2_grpc.NodeFileServiceServicer):
    def NotifyDuplicate(self, request, context):
        fname = request.filename
        # Mark as replicated (not accessible until uploader is online)
        with open(f"replicated_{fname}", "w") as f:
            f.write(f"Replicated file: {fname} from {request.id}\n")
        print(f"{Fore.MAGENTA}File '{fname}' replicated by controller. It will be accessible if uploader is online.{Style.RESET_ALL}")
        return storage_pb2.Response(message=f"Replicated file {fname} stored.")
    # Handle notification from controller to store a ghosted file
    def NotifyDuplicate(self, request, context):
        fname = request.filename
        # Mark as ghosted (not accessible until uploader is online)
        with open(f"Replicated_{fname}", "w") as f:
            f.write(f"Replicate file: {fname} from {request.id}\n")
        print(f"{Fore.MAGENTA}File '{fname}' Replicated by controller. It will be accessible if uploader is online.{Style.RESET_ALL}")
        return storage_pb2.Response(message=f"Replicated file {fname} stored.")
    def DownloadFile(self, request, context):
        fname = request.filename
        if os.path.exists(fname):
            with open(fname, "rb") as f:
                data = f.read()
            return storage_pb2.FileContent(filename=fname, content=data)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("File not found on node")
        return storage_pb2.FileContent()


def serve_node_file_service(host, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    storage_pb2_grpc.add_NodeFileServiceServicer_to_server(NodeFileService(), server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    return server


# ---------------- Main Node Terminal ----------------
def run_node(node_id, controller_host, controller_port, host="127.0.0.1", port=5000):
    # Start file service for this node
    try:
        file_server = serve_node_file_service(host, port)
    except Exception as e:
        print(f"\n{Fore.RED}Failed to bind to {host}:{port}. Is another node using this port?{Style.RESET_ALL}")
        print(f"Error: {e}")
        return

    # Connect to controller
    channel = grpc.insecure_channel(f"{controller_host}:{controller_port}")
    stub = storage_pb2_grpc.StorageControllerStub(channel)

    # Register node
    response = stub.RegisterNode(storage_pb2.NodeInfo(id=node_id, address=host, port=port))
    print(f"[Node {node_id}] {response.message}")
    print(f"{Fore.GREEN}[Node {node_id}] Node is online!{Style.RESET_ALL}")

    # Track files created in this VM
    created_files = set()
    downloaded_files = set()
    uploaded_files = set()
    try:
        import threading
        stop_flag = threading.Event()
        def heartbeat_loop():
            while not stop_flag.is_set():
                hb = stub.Heartbeat(storage_pb2.NodeInfo(id=node_id, address=host, port=port))
                # Only print once at start
                stop_flag.wait(5)

        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()
        while True:
            cmd = input(f"{Fore.BLUE}[Node {node_id}] == {node_id}$ {Style.RESET_ALL}").strip().split()
            if not cmd:
                continue
            action = cmd[0].lower()

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if action == "exit":
                print(f"[Node {node_id}] Exiting...")
                # Notify controller this VM is going offline
                try:
                    stub.SetOffline(storage_pb2.NodeInfo(id=node_id, address=host, port=port))
                except Exception:
                    pass
                stop_flag.set()
                print(f"{Fore.RED}[Node {node_id}] Node is offline! ({now}){Style.RESET_ALL}")
                break

            elif action == "help":
                print(f"""
{Fore.CYAN}create <filename>{Style.RESET_ALL}      - Create a new text file
{Fore.CYAN}modify <filename>{Style.RESET_ALL}      - Modify an existing text file
{Fore.CYAN}delete <filename>{Style.RESET_ALL}      - Delete a text file
{Fore.CYAN}upload <filename>{Style.RESET_ALL}      - Upload (announce) a file to the controller
{Fore.CYAN}download <filename>{Style.RESET_ALL}    - Download a file from another node
{Fore.CYAN}list{Style.RESET_ALL}                   - List files on the cloud/controller
{Fore.CYAN}ls{Style.RESET_ALL}                     - List files created in this VM
{Fore.CYAN}cat <filename>{Style.RESET_ALL}         - Show content of a local file
{Fore.CYAN}exit{Style.RESET_ALL}                   - Exit node terminal
                """)

            elif action == "ls":
                # Only show files created in this VM
                print("Files created in this VM:", ", ".join(created_files) if created_files else "None")

            elif action == "cat" and len(cmd) > 1:
                fname = cmd[1]
                if not os.path.exists(fname):
                    print(f"File '{fname}' does not exist.")
                else:
                    with open(fname, "r", encoding="utf-8") as f:
                        print(f"\n--- {fname} ---")
                        for line in f:
                            print(line.rstrip())

            elif action == "create" and len(cmd) > 1:
                fname = cmd[1]
                if os.path.exists(fname):
                    print("File already exists.")
                else:
                    content = input("Enter text for new file: ")
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(content)
                    created_files.add(fname)
                    print(f"Created file {fname} at {now}.")

            elif action == "modify" and len(cmd) > 1:
                fname = cmd[1]
                if not os.path.exists(fname):
                    print("File does not exist.")
                else:
                    content = input("Enter new text (will overwrite): ")
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Modified file {fname} at {now}.")

            elif action == "delete" and len(cmd) > 1:
                fname = cmd[1]
                if not os.path.exists(fname):
                    print("File does not exist.")
                else:
                    os.remove(fname)
                    created_files.discard(fname)
                    print(f"Deleted file {fname} at {now}.")

            elif action == "upload" and len(cmd) > 1:
                fname = cmd[1]
                if os.path.exists(fname):
                    print(f"{Fore.YELLOW}Uploading {fname}...{Style.RESET_ALL}", end=" ")
                    start_time = time.time()
                    resp = stub.AnnounceFile(
                        storage_pb2.FileAnnouncement(id=node_id, address=host, port=port, filename=fname)
                    )
                    elapsed = time.time() - start_time
                    uploaded_files.add(fname)
                    print(f"Done in {elapsed:.2f} seconds at {now}.")
                    print(resp.message)
                else:
                    print("File not found locally")

            elif action == "download" and len(cmd) > 1:
                fname = cmd[1]
                print(f"{Fore.YELLOW}Downloading {fname}...{Style.RESET_ALL}", end=" ")
                start_time = time.time()
                locs = stub.GetFileLocations(storage_pb2.FileName(filename=fname))
                if not locs.nodes:
                    print("No node has this file.")
                else:
                    node = random.choice(locs.nodes)
                    peer_channel = grpc.insecure_channel(f"{node.address}:{node.port}")
                    peer_stub = storage_pb2_grpc.NodeFileServiceStub(peer_channel)
                    try:
                        file_content = peer_stub.DownloadFile(storage_pb2.FileDownloadRequest(filename=fname))
                        elapsed = time.time() - start_time
                        if file_content.filename:
                            local_name = file_content.filename
                            with open(local_name, "wb") as f:
                                f.write(file_content.content)
                            created_files.add(local_name)
                            print(f"Done in {elapsed:.2f} seconds at {now}.")
                            print(f"Downloaded {fname}")
                        else:
                            print(f"Failed in {elapsed:.2f} seconds.")
                            print("File not found on peer node.")
                    except grpc.RpcError as e:
                        elapsed = time.time() - start_time
                        print(f"Failed in {elapsed:.2f} seconds.")
                        print("Download failed:", e.details())

            elif action == "list":
                # List files on the cloud/controller
                file_list = stub.ListFiles(storage_pb2.NodeInfo(id=node_id, address=host, port=port))
                print("Files on cloud:", ", ".join(file_list.filenames) if file_list.filenames else "None")

            else:
                print("Unknown command. Type 'help' for available commands.")

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n[Node {node_id}] Shutting down...")
        print(f"{Fore.RED}[Node {node_id}] Node is offline!{Style.RESET_ALL}")
        file_server.stop(0)
