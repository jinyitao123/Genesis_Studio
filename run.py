from backend.app import create_app
from backend.routes.websocket import socketio, FLASK_SOCKETIO_AVAILABLE

app = create_app()


if __name__ == "__main__":
    if FLASK_SOCKETIO_AVAILABLE and socketio:
        socketio.run(
            app,
            host="0.0.0.0",
            port=5000,
            debug=app.config["SETTINGS"].flask_debug,
            allow_unsafe_werkzeug=True,
        )
    else:
        # Fallback to standard Flask development server
        app.run(host="0.0.0.0", port=5000, debug=app.config["SETTINGS"].flask_debug)
