import os

from app.main import app

if __name__ == "__main__":
    # Keep debugger enabled, but disable the auto-reloader.
    # The workflow run/build endpoints write files under output/, and the
    # reloader can restart the process mid-request causing proxy ECONNRESET.
    port = int(os.getenv("PORT", "5007"))
    app.run(debug=True, use_reloader=False, port=port, threaded=True)
