"""
ArthSathi — Flask Backend
==========================
Main application entry point.

Runs on: http://localhost:5000
"""

import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), 'config', '.env'))

# ── Add ml-model to path so recommender.py can be imported ───
ML_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml-model')
sys.path.insert(0, os.path.abspath(ML_MODEL_PATH))

# ── Create Flask app ──────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'arthsathi_secret_key_2026')

# ── Allow frontend to call this backend ──────────────────────
# CORS = Cross Origin Resource Sharing
# This lets our HTML frontend (on port 5500) talk to Flask (port 5000)
CORS(app)

# ── Register route blueprints ─────────────────────────────────
# Each file in /routes handles one group of APIs
from routes.auth    import auth_bp
from routes.profile import profile_bp
from routes.schemes import schemes_bp

app.register_blueprint(auth_bp,    url_prefix='/api/auth')
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(schemes_bp, url_prefix='/api/schemes')

# ── Health check route ────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status' : 'ok',
        'app'    : 'ArthSathi Backend',
        'version': '1.0.0'
    })

# ── Run ───────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    print(f"\n  ArthSathi backend running on http://localhost:{port}\n")
    app.run(debug=True, port=port)
