import threading
import os
from app import create_app
from app.extensions import socketio
from worker.bot_runner import run_bot_loop

app = create_app()

def start_worker_thread():
    """Launches the bot execution loop in a background daemon thread."""
    worker_thread = threading.Thread(target=run_bot_loop, args=(app,), daemon=True)
    worker_thread.start()
    print("TradeMerc Bot Worker thread successfully launched in background.")

if __name__ == '__main__':
    # Start worker thread
    start_worker_thread()
    
    port = int(os.getenv("PORT", 5000))
    print(f"Starting TradeMerc Backend Server on port {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
