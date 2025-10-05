import os
from project_echo.web_server import app, setup_directories
import webbrowser
import threading

# ==========================================================================
# >> CONFIGURATION
# ==========================================================================
HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"

# ==========================================================================
# >> MAIN EXECUTION
# ==========================================================================
if __name__ == '__main__':
    # Ensure necessary directories exist before starting
    setup_directories()

    # Open the web browser automatically after a short delay
    # This gives the server a moment to start up
    threading.Timer(1, lambda: webbrowser.open_new(URL)).start()

    # Run the Flask web server
    app.run(host=HOST, port=PORT, debug=True, use_reloader=False)
