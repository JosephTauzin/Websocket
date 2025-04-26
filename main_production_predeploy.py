from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading
from threading import Timer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f8470y009Pi1Nw7LFW36Q9P702rCEr'
socketio = SocketIO(app, cors_allowed_origins="*")

sessions = {}
lock_timers = {}

def unlock_student(session_code):
    """ Resets the is_student_locked flag after a timeout """
    if session_code in sessions:
        sessions[session_code]['is_student_locked'] = False
        socketio.emit('student_unlocked', {'is_student_locked': False}, room=session_code)

def reset_timer(session_code):
    """ Resets or initializes the timer for a session """
    if session_code in lock_timers:
        lock_timers[session_code].cancel()
    lock_timers[session_code] = Timer(5400, check_activity, [session_code])
    lock_timers[session_code].start()

def check_activity(session_code):
    """ Check if there has been activity before deciding to unlock the student """
    if session_code in sessions and not sessions[session_code]['is_student_locked']:
        unlock_student(session_code)

@socketio.on('connect')
def on_connect():
    session_code = request.args.get('session_code')
    join_room(session_code)
    if session_code not in sessions:
        sessions[session_code] = {
            "background_image": "",
            "paths": [],
            "path_const": [],
            "is_student_locked": False,
            "is_quiz": False,
            "codes": []  # Initialize an empty list to store codes
        }
    reset_timer(session_code)
    emit('session_data', sessions[session_code], to=request.sid)

@socketio.on('add_code')
def handle_add_code(data):
    session_code = data['session_code']
    new_code = data['code']
    if session_code in sessions:
        sessions[session_code]['codes'].append(new_code)
        emit('code_added', {'new_code': new_code}, room=session_code)
        reset_timer(session_code)

@socketio.on('get_all_codes')
def handle_get_all_codes(data):
    session_code = data['session_code']
    if session_code in sessions:
        emit('all_codes', {'codes': sessions[session_code]['codes']}, room=session_code)


@socketio.on('set_student_lock')
def set_student_lock(data):
    session_code = data['session_code']
    is_locked = data['is_locked']
    if session_code in sessions:
        sessions[session_code]['is_student_locked'] = is_locked
        emit('student_lock_status', {'is_student_locked': is_locked}, room=session_code)
        reset_timer(session_code)

@socketio.on('update_background')
def handle_background_update(data):
    session_code = data['session_code']
    new_background_image = data['background_image']
    sessions[session_code]['background_image'] = new_background_image
    reset_timer(session_code)
    emit('background_update', {'background_image': new_background_image}, room=session_code, skip_sid=request.sid)

@socketio.on('update_paths')
def handle_paths_update(data):
    session_code = data['session_code']
    new_paths = data['paths']
    sessions[session_code]['paths'] = new_paths
    reset_timer(session_code)
    emit('paths_update', {'paths': sessions[session_code]['paths']}, room=session_code, skip_sid=request.sid)

@socketio.on('clear_paths')
def clear_paths(data):
    session_code = data['session_code']
    sessions[session_code]['paths'] = []
    reset_timer(session_code)
    emit('paths_cleared', {'paths': []}, room=session_code)

@socketio.on('clear_background')
def clear_background(data):
    session_code = data['session_code']
    sessions[session_code]['background_image'] = ""
    reset_timer(session_code)
    emit('background_cleared', {'background_image': ""}, room=session_code)

@socketio.on('set_quiz_status')
def set_quiz_status(data):
    session_code = data['session_code']
    is_quiz = data['is_quiz']
    if session_code in sessions:
        sessions[session_code]['IsQuiz'] = is_quiz
        emit('quiz_status_updated', {'IsQuiz': is_quiz}, room=session_code)
        reset_timer(session_code)

@socketio.on('get_quiz_status')
def get_quiz_status(data):
    session_code = data['session_code']
    if session_code in sessions:
        emit('quiz_status', {'IsQuiz': sessions[session_code]['IsQuiz']}, room=session_code)

@socketio.on('disconnect')
def on_disconnect():
    session_code = request.args.get('session_code')
    if session_code:
        leave_room(session_code)
        if session_code in lock_timers:
            lock_timers[session_code].cancel()
            del lock_timers[session_code]  # Clean up the timer object
        if session_code in sessions:
            del sessions[session_code]  # Clean up the session data

@app.route('/')
def home():
    return "This website is working!"

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)