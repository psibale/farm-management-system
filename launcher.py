import threading
import time
import logging
import webview

from app import app

HOST = "0.0.0.0"      # Change to 127.0.0.1 for local-only
PORT = 5000

WINDOW_URL = f"http://127.0.0.1:{PORT}"


def run_flask():
    # Hide Flask request logs
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":

    # Start Flask server in background
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Allow Flask to initialize
    time.sleep(2)

    # Desktop application window
    webview.create_window(
        title="Farm Management System",
        url=WINDOW_URL,
        width=1600,
        height=950,
        min_size=(1200, 800),
        resizable=True
    )

    # Start PyWebView
    webview.start()