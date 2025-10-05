from project_echo.web_server import app, setup_directories

if __name__ == "__main__":
    # This function ensures that all necessary folders like 'sessions', 'audiences', etc. exist.
    setup_directories()

    # We removed the automatic browser opening because it can be unreliable.
    # Instead, we print a clear message for you to open the browser manually.
    print("\n--- Project Echo Server is Starting ---")
    print("--- Open your browser and navigate to: http://127.0.0.1:5000 ---")
    print("--- Press CTRL+C here to stop the server. ---\n")

    # Run the Flask web server.
    # use_reloader=False is critical for the background campaign threads to work correctly.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
