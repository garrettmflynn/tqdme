import json
from flask import Flask, request, jsonify, send_file
from flask_cors import cross_origin
from flask_socketio import SocketIO, join_room, leave_room

not_found_message = "<main style='padding: 25px'><h1>404 Error — No index.html found in the base path.</h1><p>Please provide one to visualize `tqdm` updates.</p></main>"

class Server:
    
    def __init__(self, base_path, host, port):
        self.base = base_path
        self.host = host
        self.port = port
        self.app, self.socketio = create(base_path, host, port)

    def run(self):
        self.socketio.run(self.app, host=self.host, port=self.port)

    def get_url(self, metadata):
        return get_url(self.host, self.port, metadata)

def get_url(host, port, metadata):
    ip = metadata["ip"]
    page_id = str(ip)
    return f"http://{host}:{port}/view/{page_id}" 

def create(base_path, host, port):

    app = Flask(__name__)
    app.config['CORS_HEADERS'] = 'Content-Type'
    socketio = SocketIO(app, cors_allowed_origins="*")

    STATES = {}

    @app.route('/')
    def index():
        try:
            return send_file(base_path / 'index.html')
        except:
            return not_found_message


    @app.route('/view/<path:path>')
    def view(path):
        try:
            return send_file(base_path / 'index.html')
        except:
            return not_found_message

    @app.route('/update', methods=['POST'])
    @cross_origin()
    def update():
        data = json.loads(request.data) if request.data else {}

        to_return = data.get("requests", {})
        ip = data["ip"] = request.remote_addr # Add request IP address

        # Send to frontend
        socketio.emit('progress', data, room=ip)

        response = dict( ok = True )

        # Create pages for each unique IP address
        page_id = str(ip)
        identifier = f"{data['ppid']}/{data['pid']}/{data['id']}"
        group_exists = page_id in STATES
        if not group_exists:
            STATES[page_id] = {}      
            url = get_url(host, port, data)
            socketio.emit('onipadded', dict(id = page_id, url = url ))

        STATES[page_id][identifier] = data["format"]

        if to_return.get("url"):
            response["url"] = get_url(host, port, dict(ip=ip))

        return jsonify(response)
    
    @socketio.on('subscribe')
    def subscribe(page_id):
        ip = page_id
        join_room(ip) # Join room with IP address
        socketio.emit('init', dict(ip=ip, states=STATES.get(ip, {}))) # Send initial state to client

    @socketio.on('unsubscribe')
    def unsubscribe(page_id):
        ip = page_id
        leave_room(ip) # Leave room with IP address


    @socketio.on('discover')
    def discover():
        ips = {}
        for ip in STATES.keys():
            ips[ip] = get_url(host, port, dict(ip=ip))
        socketio.emit('ips', ips)
    

    @socketio.on('connect')
    def handle_connect(socket):
        print('Client connected')

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    return app, socketio
