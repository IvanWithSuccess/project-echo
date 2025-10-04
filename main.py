
from project_echo import web_server

if __name__ == "__main__":
    # This will run the Flask development server
    web_server.app.run(host='0.0.0.0', port=8080, debug=True)

