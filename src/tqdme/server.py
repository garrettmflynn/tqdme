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

        self.states = {}
        self.ip_to_user_map = {}

        self.app, self.socketio = self.create(base_path)

    def run(self):
        self.socketio.run(self.app, host=self.host, port=self.port)

    def get_pathname(self, metadata):
        user_id = metadata["user_id"]
        page_id = str(user_id)
        return f"/view/{page_id}" 

    def get_response(self, metadata):
        response = dict( ok = True )

        if metadata.get("pathname"):
            response["pathname"] =self.get_pathname(dict(user_id=metadata["user_id"]))

        return jsonify(response)

    def get_page_id(self, metadata):
        return str(metadata['user_id'])

    def update_states(self, metadata):
        page_id = self.get_page_id(metadata)
        identifier = f"{metadata['parent']}/{metadata['group']}/{metadata['id']}"

        changes = dict( user_id = None, id = None )

        if page_id not in self.states:
            self.states[page_id] = {}
            changes["user_id"] = True
            
        if identifier not in self.states[page_id]:
            self.states[page_id][identifier] = dict(done = False)
            changes["id"] = True

        state = self.states[page_id][identifier]
        state.update(metadata)

        if metadata.get("done"):
            changes["id"] = False

        return state, changes


    def get_client_id(self, metadata):

        user_id = metadata.get("user_id")
        if not user_id:
            forwarded_for = request.headers.get('X-Forwarded-For')

            ip_address = forwarded_for.split(',')[0] if forwarded_for else request.remote_addr  # Add request IP address as the unique User ID
            
            user_id = self.ip_to_user_map.get(ip_address)
            if (user_id is None):
                user_id = self.ip_to_user_map[ip_address] = len(self.ip_to_user_map) + 1

        return user_id

    def update_state(self, metadata):

        metadata["user_id"] = self.get_client_id(metadata)

        state, changes = self.update_states(metadata)

        user_changes = changes.get("user_id")
        if user_changes:
            pathname = self.get_pathname(metadata)
            message = 'onremoved' if not user_changes else 'onadded'
            self.socketio.emit(message, dict(id = self.get_page_id(metadata), pathname = pathname ))

        id_changes = changes.get("id")
        if id_changes is not None:
            message = 'onstart' if id_changes else 'onend'
            self.socketio.emit(message, dict(id = metadata['id']))

        return state

    def create(self, base_path):

        app = Flask(__name__)
        app.config['CORS_HEADERS'] = 'Content-Type'
        socketio = SocketIO(app, cors_allowed_origins="*")

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
            self.update_state(data)
            return self.get_response(data)

        @app.route('/update', methods=['POST'])
        @cross_origin()
        def update():
            data = json.loads(request.data) if request.data else {}

            state = self.update_state(data)
            
            # Send to frontend
            socketio.emit('progress', state, room=state["user_id"])

            # Create pages for each User ID
            return self.get_response(data)

        
        @socketio.on('subscribe')
        def subscribe(page_id):
            user_id = page_id
            join_room(user_id) # Join room with User ID
            socketio.emit('init', dict(user_id=user_id, states=self.states.get(user_id, {}))) # Send initial state to client

        @socketio.on('unsubscribe')
        def unsubscribe(page_id):
            user_id = page_id
            leave_room(user_id) # Leave room with User ID


        @socketio.on('discover')
        def discover():
            user_ids = {}
            for user_id in self.states.keys():
                user_ids[user_id] = self.get_pathname(dict(user_id=user_id))
            socketio.emit('users', user_ids)

        return app, socketio
