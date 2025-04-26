from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from diff_match_patch import diff_match_patch

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f8470y009Pi1Nw7LFW36Q9P702rCEr'
socketio = SocketIO(app, cors_allowed_origins="*")

dmp = diff_match_patch()


sessions = {}

@app.route('/')
def index():
    return "Welcome to the Flask-SocketIO Server!"

@socketio.on('connect')
def on_connect():
    session_code = request.args.get('session_code')
    join_room(session_code)
    if session_code not in sessions:
        sessions[session_code] = {
            "background_image": "",
            "paths": ""  # Store paths as a single string to facilitate diff/patch operations
        }
    emit('session_data', sessions[session_code], room=request.sid)

@socketio.on('update_paths')
def handle_paths_update(data):
    session_code = data['session_code']  # Extract session_code from data if sent this way
    current_paths = sessions[session_code]['paths']
    new_paths_patch = data['path_patch']
    patched_paths, _ = dmp.patch_apply(dmp.patch_fromText(new_paths_patch), current_paths)
    sessions[session_code]['paths'] = patched_paths
    emit('paths_update', {'path_patch': new_paths_patch}, room=session_code)

@socketio.on('update_background')
def handle_background_update(data):
    # Extract session_code and background_image from data
    session_code = data['session_code']
    new_background_image = data['background_image']

    # Update the session data with the new background image
    sessions[session_code]['background_image'] = new_background_image

    # Emit the updated background image to all clients in the session
    emit('background_update', {'background_image': new_background_image}, room=session_code)

@socketio.on('disconnect')
def on_disconnect():
    session_code = request.args.get('session_code')
    leave_room(session_code)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)