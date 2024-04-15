from src.tqdme.server import Server

if __name__ == "__main__":
    server = Server('localhost', 3768)
    server.run()