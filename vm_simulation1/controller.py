import grpc # type: ignore
from concurrent import futures
import time
import threading

from proto import storage_pb2, storage_pb2_grpc


registered_nodes = {}  # id -> (address, port, online, last_seen)
file_locations = {}    # filename -> { 'owners': set of (id, address, port), 'upload_time': str }


class StorageController(storage_pb2_grpc.StorageControllerServicer):
    def SetOffline(self, request, context):
        # Mark node as offline immediately
        if request.id in registered_nodes:
            addr, port, _, last_seen = registered_nodes[request.id]
            registered_nodes[request.id] = (addr, port, False, last_seen)
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[Controller] Node {request.id} set OFFLINE at {now} (by VM exit)")
            return storage_pb2.Response(message=f"Node {request.id} set offline at {now}")
        return storage_pb2.Response(message="Node not found")
    def RegisterNode(self, request, context):
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        registered_nodes[request.id] = (request.address, request.port, True, now)
        print(f"[Controller] Node {request.id} registered at {request.address}:{request.port} ONLINE at {now}")
        return storage_pb2.Response(message=f"Node {request.id} registered successfully at {now}")

    def Heartbeat(self, request, context):
        if request.id in registered_nodes:
            addr, port, _, _ = registered_nodes[request.id]
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            registered_nodes[request.id] = (addr, port, True, now)
        return storage_pb2.Response(message="Heartbeat received")

    def AnnounceFile(self, request, context):
        # Node tells controller it has a file (using FileAnnouncement)
        if request.id not in registered_nodes:
            return storage_pb2.Response(message="Node not registered")
        loc = (request.id, request.address, request.port)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        if request.filename not in file_locations:
            file_locations[request.filename] = {'owners': set(), 'upload_time': now}
        file_locations[request.filename]['owners'].add(loc)
        file_locations[request.filename]['upload_time'] = now
        print(f"[Controller] Node {request.id} announced file {request.filename} at {now}")
        # Notify all other online VMs to ghost/duplicate the file
        for nid, (addr, port, online, _) in registered_nodes.items():
            if nid != request.id and online:
                try:
                    channel = grpc.insecure_channel(f"{addr}:{port}")
                    stub = storage_pb2_grpc.NodeFileServiceStub(channel)
                    stub.NotifyDuplicate(request)
                    print(f"[Controller] Notified {nid} to ghost file {request.filename}")
                except Exception as e:
                    print(f"[Controller] Failed to notify {nid}: {e}")
        return storage_pb2.Response(message=f"File {request.filename} announced by {request.id} at {now}")

    def GetFileLocations(self, request, context):
        # Return all online nodes that have the file
        filename = request.filename
        nodes = []
        if filename in file_locations:
            for nid, addr, port in file_locations[filename]['owners']:
                if nid in registered_nodes and registered_nodes[nid][2]:  # online
                    nodes.append(storage_pb2.NodeLocation(id=nid, address=addr, port=port))
        return storage_pb2.NodeLocationList(nodes=nodes)

    def CreateFile(self, request, context):
        # Just for compatibility, does nothing
        return storage_pb2.Response(message=f"File {request.filename} create requested (noop)")

    def DeleteFile(self, request, context):
        # Remove file from all nodes
        fname = request.filename
        if fname in file_locations:
            del file_locations[fname]
            print(f"[Controller] Deleted file record: {fname}")
            return storage_pb2.Response(message=f"Deleted {fname}")
        return storage_pb2.Response(message="File not found")

    def ModifyFile(self, request, context):
        # Not implemented in controller
        return storage_pb2.Response(message="Modify not supported at controller")

    def ListFiles(self, request, context):
        # Only show files uploaded by online VMs
        visible_files = []
        for fname, info in file_locations.items():
            # At least one owner must be online
            for nid, addr, port in info['owners']:
                if nid in registered_nodes and registered_nodes[nid][2]:
                    visible_files.append(fname)
                    break
        return storage_pb2.FileList(filenames=visible_files)

def serve_controller(host="127.0.0.1", port=6000):
    print(f"[DEBUG] serve_controller called with host={host}, port={port}")
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        storage_pb2_grpc.add_StorageControllerServicer_to_server(StorageController(), server)
        server.add_insecure_port(f"{host}:{port}")
        print(f"[Controller] Running on {host}:{port}")
        server.start()
        while True:
            # Check for offline nodes and remove their files from cloud
            now = time.time()
            offline_nodes = []
            for nid, (addr, port, online, last_seen) in registered_nodes.items():
                # If last seen > 15 seconds ago, mark offline
                last_seen_time = time.mktime(time.strptime(last_seen, '%Y-%m-%d %H:%M:%S'))
                if online and now - last_seen_time > 15:
                    registered_nodes[nid] = (addr, port, False, last_seen)
                    print(f"[Controller] Node {nid} OFFLINE at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    offline_nodes.append(nid)
            # Remove files from cloud if all owners are offline
            to_remove = []
            for fname, info in file_locations.items():
                online_owners = [nid for nid, _, _ in info['owners'] if nid in registered_nodes and registered_nodes[nid][2]]
                if not online_owners:
                    to_remove.append(fname)
            for fname in to_remove:
                print(f"[Controller] File {fname} removed from cloud (all owners offline)")
                del file_locations[fname]
            time.sleep(5)
    except Exception as e:
        print(f"[ERROR] Exception in serve_controller: {e}")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\n[Controller] Shutting down...")
        server.stop(0)

def start_dashboard():
    try:
        from dashboard import run_dashboard
        t = threading.Thread(target=run_dashboard, daemon=True)
        t.start()
        print("[Controller] Web dashboard running at http://127.0.0.1:8080/")
    except Exception as e:
        print(f"[Controller] Failed to start dashboard: {e}")

if __name__ == "__main__":
    start_dashboard()
    serve_controller()
