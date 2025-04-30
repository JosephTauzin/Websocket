from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from threading import Timer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f8470y009Pi1Nw7LFW36Q9P702rCEr'
socketio = SocketIO(app, cors_allowed_origins="*")

# --------------------------------------------------------------------
# In-memory session store
# --------------------------------------------------------------------
sessions = {}
lock_timers = {}
HISTORY_LIMIT = 100          # ▶ maximum snapshots per stack (tweak or remove)

# --------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------
def unlock_student(session_code):
    if session_code in sessions:
        sessions[session_code]['is_student_locked'] = False
        socketio.emit('student_unlocked', {'is_student_locked': False},
                      room=session_code)

def reset_timer(session_code):
    if session_code in lock_timers:
        lock_timers[session_code].cancel()
    lock_timers[session_code] = Timer(5400, unlock_student, [session_code])
    lock_timers[session_code].start()

# --------------------------------------------------------------------
# Socket.IO lifecycle
# --------------------------------------------------------------------
@socketio.on('connect')
def on_connect():
    session_code = request.args.get('session_code')
    join_room(session_code)

    if session_code not in sessions:
        sessions[session_code] = {
            "background_image": "",
            "paths": [],
            "undo_stack": [],   # ▶
            "redo_stack": [],   # ▶
            "is_student_locked": False,
            "is_quiz": False
        }
    reset_timer(session_code)
    emit('session_data', sessions[session_code], to=request.sid)

@socketio.on('disconnect')
def on_disconnect():
    session_code = request.args.get('session_code')
    if not session_code:
        return
    leave_room(session_code)
    if session_code in lock_timers:
        lock_timers[session_code].cancel()
        del lock_timers[session_code]
    sessions.pop(session_code, None)

# --------------------------------------------------------------------
# Lock / quiz status (unchanged)
# --------------------------------------------------------------------
@socketio.on('set_student_lock')
def set_student_lock(data):
    session_code = data['session_code']
    is_locked = data['is_locked']
    if session_code in sessions:
        sessions[session_code]['is_student_locked'] = is_locked
        emit('student_lock_status', {'is_student_locked': is_locked},
             room=session_code)
        reset_timer(session_code)

@socketio.on('set_quiz_status')
def set_quiz_status(data):
    session_code = data['session_code']
    is_quiz = data['is_quiz']
    if session_code in sessions:
        sessions[session_code]['is_quiz'] = is_quiz
        emit('quiz_status_updated', {'is_quiz': is_quiz}, room=session_code)
        reset_timer(session_code)

@socketio.on('get_quiz_status')
def get_quiz_status(data):
    session_code = data['session_code']
    if session_code in sessions:
        emit('quiz_status', {'is_quiz': sessions[session_code]['is_quiz']},
             room=session_code)

# --------------------------------------------------------------------
# Background image
# --------------------------------------------------------------------
@socketio.on('update_background')
def handle_background_update(data):
    session_code = data['session_code']
    new_bg = data['background_image']
    sessions[session_code]['background_image'] = new_bg
    reset_timer(session_code)
    emit('background_update', {'background_image': new_bg},
         room=session_code, skip_sid=request.sid)

@socketio.on('clear_background')
def clear_background(data):
    session_code = data['session_code']
    sessions[session_code]['background_image'] = ""
    reset_timer(session_code)
    emit('background_cleared', {'background_image': ""}, room=session_code)

# --------------------------------------------------------------------
# Path handling – now with history support!
# --------------------------------------------------------------------
def _push_history(stack, snapshot):
    """Utility to cap stack length and push a snapshot"""
    stack.append(snapshot)
    if HISTORY_LIMIT and len(stack) > HISTORY_LIMIT:
        stack.pop(0)

@socketio.on('update_paths')
def handle_paths_update(data):
    session_code = data['session_code']
    new_paths = data['paths']

    # ▶ Save current state for undo *before* we overwrite it
    current_paths = sessions[session_code]['paths']
    _push_history(sessions[session_code]['undo_stack'], current_paths.copy())
    sessions[session_code]['redo_stack'].clear()   # fresh change breaks redo chain

    # ▶ Apply new paths
    sessions[session_code]['paths'] = new_paths
    reset_timer(session_code)
    emit('paths_update', {'paths': new_paths},
         room=session_code, skip_sid=request.sid)

@socketio.on('clear_paths')
def clear_paths(data):
    session_code = data['session_code']
    current = sessions[session_code]['paths']
    _push_history(sessions[session_code]['undo_stack'], current.copy())
    sessions[session_code]['redo_stack'].clear()

    sessions[session_code]['paths'] = []
    reset_timer(session_code)
    emit('paths_cleared', {'paths': []}, room=session_code)

# --------------------------------------------------------------------
# NEW: undo / redo
# --------------------------------------------------------------------
@socketio.on('undo_request')
def handle_undo(data):
    session_code = data['session_code']
    sess = sessions.get(session_code)
    if not sess or not sess['undo_stack']:
        return  # nothing to undo

   

    emit('undo', {'paths': sess['paths']}, room=session_code)

@socketio.on('redo_request')
def handle_redo(data):
    session_code = data['session_code']
    sess = sessions.get(session_code)
    if not sess or not sess['redo_stack']:
        return  # nothing to redo



    emit('redo', {'paths': sess['paths']}, room=session_code)

# --------------------------------------------------------------------
# Misc
# --------------------------------------------------------------------
@app.route('/')
def home():
    return "This website is working!"

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
