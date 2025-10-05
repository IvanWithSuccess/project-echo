import os
import logging
from project_echo.web_server import app, setup_directories

if __name__ == "__main__":
    # Set up necessary folders like 'sessions', 'uploads', etc.
    setup_directories()

    # Get the host and port from environment variables or use defaults
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", 5000))

    logging.info(f"Starting Project Echo server at http://{host}:{port}")
    
    # --- CRITICAL --- 
    # debug=True automatically enables the reloader and disables caching.
    # This is essential for development.
    # use_reloader=False is set to prevent conflicts with background tasks if we add them later.
    app.run(host=host, port=port, debug=True, use_reloader=False)
