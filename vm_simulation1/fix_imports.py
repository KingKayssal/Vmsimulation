# fix_imports.py
import os

def fix_proto_imports():
    grpc_file = "proto/storage_pb2_grpc.py"
    
    if not os.path.exists(grpc_file):
        print(f"Error: {grpc_file} not found")
        return False
        
    with open(grpc_file, 'r') as f:
        content = f.read()
    
    # Replace absolute import with relative import
    fixed_content = content.replace(
        'import storage_pb2 as storage__pb2',
        'from . import storage_pb2 as storage__pb2'
    )
    
    with open(grpc_file, 'w') as f:
        f.write(fixed_content)
    
    print("Fixed imports in storage_pb2_grpc.py")
    return True

if __name__ == "__main__":
    fix_proto_imports()