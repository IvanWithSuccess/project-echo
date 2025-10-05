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

    # DEFINITIVE FIX: Use open_new_tab() to explicitly open a new tab.
    threading.Timer(1, lambda: webbrowser.open_new_tab(URL)).start()

    # Run the Flask web server
    # use_reloader=False is important to prevent the script from running twice
    app.run(host=HOST, port=PORT, debug=True, use_reloader=False)
