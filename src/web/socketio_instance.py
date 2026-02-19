"""
SocketIO instance - shared between app.py and websocket_events.py
Separating this avoids circular import issues
"""
from flask_socketio import SocketIO

# Initialize SocketIO instance (will be attached to Flask app in app.py)
socketio = SocketIO()
