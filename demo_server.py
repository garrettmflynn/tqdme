from src.tqdme.server import Server
from flask import send_from_directory
from pathlib import Path

script_directory = Path(__file__).parent.resolve()

if __name__ == "__main__":

    server = Server(script_directory, 'localhost', 3768)

    app = server.app

    @server.app.route('/src/<path:path>')
    def get_static_assets(path):
        return send_from_directory(server.base / 'src', path)

    server.run()