
import threading
import webbrowser
from project_echo.web_server import app, setup_directories

HOST = "127.0.0.1"
PORT = 5000

def run_app():
    """Runs the Flask app."""
    setup_directories()
    app.run(host=HOST, port=PORT, debug=True, use_reloader=False) # use_reloader=False is important for this setup

if __name__ == "__main__":
    # Open the web browser in a separate thread
    webbrowser.open_new(f"http://{HOST}:{PORT}")
    
    # Run the Flask app in the main thread
    run_app()
