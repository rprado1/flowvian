import os
import time
from flask import Flask, send_from_directory, abort, g, request
from app.paths import get_data_dir, get_output_dir

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DIST_DIR = os.path.join(STATIC_DIR, "dist")
DATA_DIR = get_data_dir()
OUTPUT_DIR = get_output_dir()

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
app.config["DATA_DIR"] = DATA_DIR
app.config["OUTPUT_DIR"] = OUTPUT_DIR


def _http_log_enabled() -> bool:
    return os.getenv("WBUI_HTTP_LOG", "1") != "0"


@app.before_request
def _start_request_timer():
    if _http_log_enabled():
        g._request_start = time.perf_counter()


@app.after_request
def _log_request(response):
    if _http_log_enabled():
        started = getattr(g, "_request_start", None)
        elapsed_ms = 0.0
        if started is not None:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
        print(
            f"[wbui] {request.method} {request.path} -> {response.status_code} ({elapsed_ms:.1f} ms)"
        )
    return response

print(f"[wbui] Data directory: {DATA_DIR}")
print(f"[wbui] Output directory: {OUTPUT_DIR}")

# Register blueprints
from app.api.workflows import workflows_bp
from app.api.builder import builder_bp

app.register_blueprint(workflows_bp, url_prefix="/api/workflows")
app.register_blueprint(builder_bp, url_prefix="/api/workflows")


@app.route("/assets/<path:filename>")
def dist_assets(filename):
    """Serve JS/CSS chunks emitted by Vite into dist/assets/."""
    return send_from_directory(os.path.join(DIST_DIR, "assets"), filename)


@app.route("/<path:filename>")
def dist_root_files(filename):
    """Serve root-level static files from dist/ (favicon.svg, icons.svg, etc.)
    only when the file actually exists there — otherwise fall through to the
    SPA catch-all below."""
    candidate = os.path.join(DIST_DIR, filename)
    if os.path.isfile(candidate) and not filename.startswith("api/"):
        return send_from_directory(DIST_DIR, filename)
    # Not a real file — hand off to the SPA route
    return spa_index()


@app.route("/")
def spa_index():
    """Serve the React SPA entry point."""
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return send_from_directory(DIST_DIR, "index.html")
    # Fallback before the first npm run build
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5007)
