# Distributed File Storage Simulation (ZEB Controller)

A Python-based distributed file storage simulation using gRPC and Flask. Includes a controller ("zeb controller"), multiple nodes (VMs), and a live web dashboard for monitoring and control.

## Features
- **Controller**: Manages nodes, file announcements, replication, and dashboard.
- **Nodes**: Simulate VMs, support file upload/download, and interact with the controller.
- **Web Dashboard**: Register nodes, upload/download files, and view live status of nodes/files.
- **gRPC**: For communication between controller and nodes.
- **Threading**: For dashboard and node heartbeats.

## Requirements
- Python 3.8+
- See `requirements.txt`

## Setup
1. Clone the repository and navigate to the project folder.
2. (Recommended) Create a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Generate gRPC code (if you change `proto/storage.proto`):
   ```
   python -m grpc_tools.protoc -I./proto --python_out=./proto --grpc_python_out=./proto ./proto/storage.proto
   python fix_imports.py
   ```

## Running the Simulation
### 1. Start the Controller (with Dashboard)
```
python main.py --controller --host 127.0.0.1 --port 6000
```
- The dashboard will be available at [http://127.0.0.1:8080/](http://127.0.0.1:8080/)

### 2. Start a Node (VM)
```
python main.py --node --id vm1 --controller-host 127.0.0.1 --controller-port 6000 --host 127.0.0.1 --port 5001
```
- You can start multiple nodes with different `--id` and `--port` values.

### 3. Use the Dashboard
- Register nodes, upload files, and download files directly from the web interface.
- Node and file status update live.

### 4. Node CLI Commands
- `help` — Show available commands
- `create <filename>` — Create a file
- `modify <filename>` — Modify a file
- `delete <filename>` — Delete a file
- `upload <filename>` — Upload/announce a file to the controller
- `download <filename>` — Download a file from another node
- `list` — List files on the controller
- `ls` — List files created in this VM
- `cat <filename>` — Show file content
- `exit` — Exit node

## Notes
- The dashboard simulates file upload/download (does not store real files).
- For demo/educational use only. No authentication or security.
- To regenerate gRPC code after editing the proto, see Setup step 4.

## Project Structure
- `main.py` — Entry point
- `controller.py` — Controller logic and dashboard starter
- `node.py` — Node/VM logic
- `dashboard.py` — Flask dashboard
- `proto/` — gRPC proto and generated code
- `fix_imports.py` — Fixes imports in generated gRPC code

---
MIT License
