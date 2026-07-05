import argparse
import os

from app.main import app


def main(port=None):
    final_port = int(port or os.getenv("PORT", "5007"))
    use_flask_dev_server = os.getenv("WBUI_USE_FLASK_DEV_SERVER") == "1"

    if use_flask_dev_server:
        # Development-only mode.
        app.run(debug=True, use_reloader=False, port=final_port, threaded=True)
        return

    try:
        from waitress import serve
    except Exception:
        # Fallback if waitress is not available in the environment.
        app.run(debug=False, use_reloader=False, port=final_port, threaded=True)
        return

    serve(app, host="127.0.0.1", port=final_port, threads=8)


def cli():
    parser = argparse.ArgumentParser(prog="wbui")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start Workflow Builder")
    start_parser.add_argument(
        "-p",
        dest="port",
        type=int,
        help="Port to bind the server (1-65535)",
    )

    args = parser.parse_args()
    if args.command != "start":
        parser.print_help()
        return

    if args.port is not None and not (1 <= args.port <= 65535):
        parser.error("Port must be between 1 and 65535")

    main(port=args.port)


if __name__ == "__main__":
    main()
