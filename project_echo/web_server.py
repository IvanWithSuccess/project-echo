import logging
from flask import Flask, render_template, jsonify, request
import os

# --- Basic Flask App Setup ---
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# ==========================================================================
# >> AGGRESSIVE CACHE BUSTING (DEFINITIVE FIX)
# ==========================================================================
@app.after_request
def add_header(response):
    """
    Add headers to both force latest content and prevent caching.
    This is the most aggressive and reliable method.
    """
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache' # for HTTP/1.0 compatibility
    response.headers['Expires'] = '0' # force expiration
    return response

# ==========================================================================
# >> CORE ROUTES
# ==========================================================================

@app.route('/')
def index():
    """Serves the main single-page application."""
    logging.info("Serving index.html")
    return render_template('index.html')


# This is a placeholder for our API functions. We will add them later.
@app.route('/api/placeholder')
def placeholder():
    return jsonify({"message": "API is working"})

# ==========================================================================
# >> UTILITY FUNCTIONS
# ==========================================================================

def setup_directories():
    """Creates necessary directories for the application to function."""
    logging.info("Checking and creating necessary directories...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base_dir, 'sessions'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'audiences'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'uploads'), exist_ok=True)
    logging.info("Directory setup complete.")
