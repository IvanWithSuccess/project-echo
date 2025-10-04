
from project_echo.web_server import app, setup_directories

if __name__ == '__main__':
    # Ensure necessary directories like 'sessions' and 'audiences' are created on startup
    setup_directories()
    
    # Run the Flask web server
    # In a real production environment, you would use a more robust WSGI server 
    # like Gunicorn or uWSGI instead of the built-in Flask development server.
    # Example: gunicorn --workers 4 --bind 0.0.0.0:8000 main:app
    app.run(host='0.0.0.0', port=8000, debug=True)
