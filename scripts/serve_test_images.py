import os
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestImageHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests/test_data/tables/quotations'), **kwargs)

    def do_GET(self):
        # Enable CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'image/jpeg')
        self.end_headers()

        # Serve the file
        with open(os.path.join(self.directory, os.path.basename(self.path)), 'rb') as f:
            self.wfile.write(f.read())

def start_server(port=8000):
    """Start HTTP server in a separate thread"""
    server = HTTPServer(('localhost', port), TestImageHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    logger.info(f"Server started at http://localhost:{port}")
    return server, thread

def get_image_url(image_name, port=8000):
    """Get the URL for a test image"""
    return f"http://localhost:{port}/{quote(image_name)}"

if __name__ == '__main__':
    server, thread = start_server()
    try:
        # Keep the main thread running
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
