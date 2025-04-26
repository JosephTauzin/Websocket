from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

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
            "paths": [],
            "path_const": []
        }
    # Emit existing session data to the newly connected client only
    emit('session_data', sessions[session_code], to=request.sid)

@socketio.on('update_background')
def handle_background_update(data):
    session_code = data['session_code']
    new_background_image = data['background_image']
    sessions[session_code]['background_image'] = new_background_image
    # Broadcast the new background image to all clients in the session except the sender
    emit('background_update', {'background_image': new_background_image}, room=session_code, skip_sid=request.sid)

@socketio.on('update_paths')
def handle_paths_update(data):
    session_code = data['session_code']
    new_path = data['paths']
    # Update paths for the session
    sessions[session_code]['paths'] = new_path
    #for path in new_path:
    #    sessions[session_code]['path_const'].append(path)
    # Broadcast the paths update to all clients in the session except the sender
    emit('paths_update', {'paths': sessions[session_code]['paths']}, room=session_code, skip_sid=request.sid)

@socketio.on('clear_paths')
def clear_paths(data):
    session_code = data['session_code']
    sessions[session_code]['paths'] = []
    # Broadcast the paths cleared event to all clients in the session
    emit('paths_cleared', {'paths': []}, room=session_code)


@socketio.on('clear_background')
def clear_background(data):
    session_code = data['session_code']
    sessions[session_code]['background_image'] = ""
    # Broadcast the background cleared event to all clients in the session
    emit('background_cleared', {'background_image': ""}, room=session_code)



@socketio.on('disconnect')
def on_disconnect():
    # Get the session code from the request arguments on disconnect
    session_code = request.args.get('session_code')
    if session_code:
        leave_room(session_code)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5005)
