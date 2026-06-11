import os
from flask import Flask, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "output")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
app.config["DATA_DIR"] = DATA_DIR
app.config["OUTPUT_DIR"] = OUTPUT_DIR

# Register blueprints
from app.api.workflows import workflows_bp
from app.api.builder import builder_bp

app.register_blueprint(workflows_bp, url_prefix="/api/workflows")
app.register_blueprint(builder_bp, url_prefix="/api/workflows")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
