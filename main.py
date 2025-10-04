
import webbrowser
from threading import Timer
from project_echo import web_server

def open_browser():
    # Opens the URL in a new browser tab
    webbrowser.open_new("http://127.0.0.1:8080")

if __name__ == "__main__":
    # Run open_browser in a separate thread after a short delay
    # to give the server time to start up.
    Timer(1, open_browser).start()
    
    # Run the Flask development server
    web_server.app.run(host='0.0.0.0', port=8080, debug=False)

