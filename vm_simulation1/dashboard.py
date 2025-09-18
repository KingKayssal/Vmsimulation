
from flask import Flask, render_template_string, request, redirect, send_file, flash, url_for
import threading
import time
import io
from controller import registered_nodes, file_locations

app = Flask(__name__)

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Distributed Storage Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 90%; margin: 20px auto; background: #fff; }
        th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
        th { background: #eee; }
        .online { color: green; font-weight: bold; }
        .offline { color: red; font-weight: bold; }
                .form-section { background: #e3f2fd; border-radius: 8px; padding: 16px; margin: 20px auto; width: 80%; box-shadow: 0 2px 8px #bbb; }
                .form-section h3 { color: #1976d2; }
                .btn { background: #1976d2; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
                .btn:hover { background: #1565c0; }
                .msg { color: #d32f2f; font-weight: bold; margin: 10px; }
    </style>
</head>
<body>
    <h1>Distributed Storage Dashboard</h1>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <div class="msg">{{ messages[0] }}</div>
            {% endif %}
        {% endwith %}

        <div class="form-section">
            <h3>Register Node</h3>
            <form method="post" action="/register_node">
                <label>Node ID: <input name="node_id" required></label>
                <label>Address: <input name="address" value="127.0.0.1" required></label>
                <label>Port: <input name="port" type="number" value="5001" required></label>
                <button class="btn" type="submit">Register</button>
            </form>
        </div>

        <div class="form-section">
            <h3>Upload File</h3>
            <form method="post" action="/upload_file" enctype="multipart/form-data">
                <label>Filename: <input name="filename" required></label>
                <label>Owner Node ID: <input name="owner_id" required></label>
                <input type="file" name="filedata" required>
                <button class="btn" type="submit">Upload</button>
            </form>
        </div>

        <div class="form-section">
            <h3>Download File</h3>
            <form method="get" action="/download_file">
                <label>Filename: <input name="filename" required></label>
                <button class="btn" type="submit">Download</button>
            </form>
        </div>
    <h2>Nodes</h2>
    <table>
        <tr><th>ID</th><th>Address</th><th>Port</th><th>Status</th><th>Last Seen</th></tr>
        {% for nid, (addr, port, online, last_seen) in nodes.items() %}
        <tr>
            <td>{{ nid }}</td>
            <td>{{ addr }}</td>
            <td>{{ port }}</td>
            <td class="{{ 'online' if online else 'offline' }}">{{ 'Online' if online else 'Offline' }}</td>
            <td>{{ last_seen }}</td>
        </tr>
        {% endfor %}
    </table>
    <h2>Files on Controller</h2>
    <table>
        <tr><th>Filename</th><th>Owners</th><th>Upload Time</th></tr>
        {% for fname, info in files.items() %}
        <tr>
            <td>{{ fname }}</td>
            <td>{% for owner in info['owners'] %}<span style="color:#1976d2;font-weight:bold">{{ owner[0] }}</span> ({{ owner[1] }}:{{ owner[2] }}) {% endfor %}</td>
            <td>{{ info['upload_time'] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
'''

@app.route('/')
def dashboard():
    return render_template_string(TEMPLATE, nodes=registered_nodes, files=file_locations)


# --- Web endpoints for actions ---
@app.route('/register_node', methods=['POST'])
def register_node():
    node_id = request.form['node_id']
    address = request.form['address']
    port = int(request.form['port'])
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    registered_nodes[node_id] = (address, port, True, now)
    flash(f"Node {node_id} registered at {address}:{port} (ONLINE)")
    return redirect(url_for('dashboard'))

@app.route('/upload_file', methods=['POST'])
def upload_file():
    filename = request.form['filename']
    owner_id = request.form['owner_id']
    file = request.files['filedata']
    if not file:
        flash("No file uploaded!")
        return redirect(url_for('dashboard'))
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # Simulate file storage: just record metadata
    if filename not in file_locations:
        file_locations[filename] = {'owners': set(), 'upload_time': now}
    # Use dummy address/port if owner not registered
    if owner_id in registered_nodes:
        addr, port, _, _ = registered_nodes[owner_id]
    else:
        addr, port = '127.0.0.1', 5001
    file_locations[filename]['owners'].add((owner_id, addr, port))
    file_locations[filename]['upload_time'] = now
    flash(f"File '{filename}' uploaded and owned by {owner_id}")
    return redirect(url_for('dashboard'))

@app.route('/download_file', methods=['GET'])
def download_file():
    filename = request.args.get('filename')
    if filename not in file_locations:
        flash(f"File '{filename}' not found!")
        return redirect(url_for('dashboard'))
    # Simulate file content
    content = f"Dummy content of {filename} (not actual file data)"
    return send_file(io.BytesIO(content.encode()), as_attachment=True, download_name=filename)

def run_dashboard():
    app.secret_key = 'zebcontrollersecret'
    app.run(port=8080, debug=False, use_reloader=False)

# To run the dashboard in parallel with the controller, call run_dashboard() in a thread.
