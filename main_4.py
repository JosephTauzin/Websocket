from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from diff_match_patch import diff_match_patch

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f8470y009Pi1Nw7LFW36Q9P702rCEr'
socketio = SocketIO(app, cors_allowed_origins="*")

sessions = {}

@socketio.on('connect')
def on_connect():
    session_code = request.args.get('session_code')
    join_room(session_code)
    if session_code not in sessions:
        sessions[session_code] = {
            "background_image": "",
            "paths": []
        }
    # Emit existing data when a new client connects
    emit('session_data', sessions[session_code], room=request.sid)

@socketio.on('update_background')
def handle_background_update(data):
    session_code = data['session_code']
    new_background_image = data['background_image']
    sessions[session_code]['background_image'] = new_background_image
    emit('background_update', {'background_image': new_background_image}, room=session_code)

@socketio.on('update_paths')
def handle_paths_update(data):
    session_code = data['session_code']
    new_path = data['paths']
    #for path in new_path:
        
    #sessions[session_code]['paths'].append(path)
    sessions[session_code]['paths'] = new_path
    emit('paths_update', {'paths': sessions[session_code]['paths']}, room=session_code)

@socketio.on('clear_paths')
def clear_paths(data):
    session_code = data['session_code']
    sessions[session_code]['paths'] = []
    emit('paths_cleared', {'paths': []}, room=session_code)

@socketio.on('disconnect')
def on_disconnect():
    session_code = request.args.get('session_code')
    leave_room(session_code)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5005)