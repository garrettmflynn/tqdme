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
    user_id = metadata["user_id"]
    page_id = str(user_id)
    return f"http://{host}:{port}/view/{page_id}" 

def get_response(host, port, metadata):
    response = dict( ok = True )

    if metadata.get("url"):
        response["url"] = get_url(host, port, dict(user_id=metadata["user_id"]))

    return jsonify(response)

def get_page_id(metadata):
    return str(metadata['user_id'])

def update_states(states, metadata):
    page_id = get_page_id(metadata)
    identifier = f"{metadata['parent']}/{metadata['group']}/{metadata['id']}"

    changes = dict( user_id = None, id = None )

    if page_id not in states:
        states[page_id] = {}
        changes["user_id"] = True
        
    if identifier not in states[page_id]:
        states[page_id][identifier] = dict(done = False)
        changes["id"] = True

    state = states[page_id][identifier]
    state.update(metadata)

    if metadata.get("done"):
        changes["id"] = False

    return state, changes


def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def create(base_path, host, port):

    STATES = {}

    app = Flask(__name__)
    app.config['CORS_HEADERS'] = 'Content-Type'
    socketio = SocketIO(app, cors_allowed_origins="*")

    def update_local_state(metadata):

        if (not metadata.get("user_id")):
            metadata["user_id"] = get_client_ip() # Add request IP address as the unique User ID

        state, changes = update_states(STATES, metadata)

        user_changes = changes.get("user_id")
        if user_changes:
            url = get_url(host, port, metadata)
            message = 'onremoved' if not user_changes else 'onadded'
            socketio.emit(message, dict(id = get_page_id(metadata), url = url ))

        id_changes = changes.get("id")
        if id_changes is not None:
            message = 'onstart' if id_changes else 'onend'
            socketio.emit(message, dict(id = metadata['id']))

        return state

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
        
    @app.route('/ping', methods=['POST'])
    @cross_origin()
    def ping():
        data = json.loads(request.data) if request.data else {}
        update_local_state(data)
        return get_response(host, port, data)

    @app.route('/update', methods=['POST'])
    @cross_origin()
    def update():
        data = json.loads(request.data) if request.data else {}

        state = update_local_state(data)
        
        # Send to frontend
        socketio.emit('progress', state, room=state["user_id"])

        # Create pages for each User ID
        return get_response(host, port, data)

    
    @socketio.on('subscribe')
    def subscribe(page_id):
        user_id = page_id
        join_room(user_id) # Join room with User ID
        socketio.emit('init', dict(user_id=user_id, states=STATES.get(user_id, {}))) # Send initial state to client

    @socketio.on('unsubscribe')
    def unsubscribe(page_id):
        user_id = page_id
        leave_room(user_id) # Leave room with User ID


    @socketio.on('discover')
    def discover():
        user_ids = {}
        for user_id in STATES.keys():
            user_ids[user_id] = get_url(host, port, dict(user_id=user_id))
        socketio.emit('users', user_ids)

    return app, socketio
