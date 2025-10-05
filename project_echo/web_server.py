import logging
from flask import Flask, render_template, jsonify, request
import os
import time

# --- Basic Flask App Setup ---
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# ==========================================================================
# >> ROUTES
# ==========================================================================

@app.route('/')
def index():
    """Serves the main single-page application with a cache-busting query string."""
    logging.info("Serving index.html with cache buster.")
    # DEFINITIVE FIX: Generate a version based on the current time.
    # This is passed to the template to append to static file URLs.
    cache_buster = str(time.time())
    return render_template('index.html', cache_buster=cache_buster)


# This is a placeholder for our API functions.
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
