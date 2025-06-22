from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask import copy_current_request_context
import string
from io import BytesIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Global variable to store questions (loaded once)
QUESTIONS = None

# Global dictionary to store active games and their state
GAMES = {}
# Structure:
# GAMES = {
#   room_code: {
#       'host': session_id,
#       'players': { session_id: { 'name': str, 'score': int, 'time': float, 'finished': bool } },
#       'questions': [...],
#       'started': bool,
#       'start_time': datetime,
#       'end_time': datetime or None
#   },
#   ...
# }

# Example short sound bytes (replace with your own or use real MP3 bytes)
CORRECT_SOUND = b"\x49\x44\x33..."  # TODO: Replace with real MP3 bytes
WRONG_SOUND = b"\x49\x44\x33..."    # TODO: Replace with real MP3 bytes
TOGGLE_SOUND = b"\x49\x44\x33..."   # TODO: Replace with real MP3 bytes

# Load questions from JSON file
def load_questions():
    global QUESTIONS
    if QUESTIONS is None:
        with open('questions.json', 'r', encoding='utf-8') as file:
            QUESTIONS = json.load(file)
    return QUESTIONS

def get_available_question_lists():
    questions = load_questions()
    return {k: len(v) for k, v in questions.items() if isinstance(v, list)}

@app.route('/get_question_lists')
def get_question_lists():
    lists = get_available_question_lists()
    return jsonify(lists)

def generate_session_id():
    """Generate a unique session ID for each user"""
    return str(uuid.uuid4())

def validate_session():
    """Validate that the current session is valid and not expired"""
    if not session.get('session_id'):
        return False
    
    # Check if session is expired (24 hours)
    session_created = session.get('session_created')
    if session_created:
        try:
            created_time = datetime.fromisoformat(session_created)
            if datetime.now() - created_time > timedelta(hours=24):
                return False
        except:
            return False
    
    return True

def create_new_session():
    """Create a new session with unique ID and timestamp"""
    session.clear()  # Clear any existing session data
    session['session_id'] = generate_session_id()
    session['session_created'] = datetime.now().isoformat()
    session['exam_started'] = False
    session['exam_submitted'] = False
    session['answers'] = {}
    session['total_questions'] = 0
    session['exam_seed'] = None
    session['randomize_questions'] = True

def randomize_questions_and_options(questions, seed=None, randomize_questions=True):
    """Randomize questions and options while maintaining correct answer tracking"""
    if seed is not None:
        random.seed(seed)
    
    randomized_questions = []
    
    for question in questions:
        # Create a copy of the question
        new_question = question.copy()
        options = list(question['options'])
        correct_index = int(question['correct_answer'])
        correct_option = options[correct_index]
        # Shuffle options and track new correct index
        option_indices = list(range(len(options)))
        random.shuffle(option_indices)
        shuffled_options = [options[i] for i in option_indices]
        new_correct_index = option_indices.index(correct_index)
        new_question['options'] = shuffled_options
        new_question['correct_answer'] = new_correct_index
        randomized_questions.append(new_question)
    
    # Randomize question order if requested
    if randomize_questions:
        random.shuffle(randomized_questions)
    
    return randomized_questions

@app.route('/')
def index():
    """Root page - automatically start exam and redirect to exam page"""
    # Validate or create new session
    if not validate_session():
        create_new_session()
    
    # Load questions to ensure they're available
    questions = load_questions()
    
    # Generate a random seed for consistent randomization
    exam_seed = random.randint(1, 1000000)
    
    # Store only essential data in session
    session['exam_started'] = True
    session['answers'] = {}
    session['total_questions'] = len(questions)
    session['exam_seed'] = exam_seed
    session['randomize_questions'] = True  # Default to true
    
    return redirect(url_for('exam'))

@app.route('/start_exam')
def start_exam():
    """Initialize exam session and redirect to exam page"""
    # Validate or create new session
    if not validate_session():
        create_new_session()
    
    # Load questions to ensure they're available
    questions = load_questions()
    
    # Generate a random seed for consistent randomization
    exam_seed = random.randint(1, 1000000)
    
    # Store only essential data in session
    session['exam_started'] = True
    session['answers'] = {}
    session['total_questions'] = len(questions)
    session['exam_seed'] = exam_seed
    session['randomize_questions'] = True  # Default to true
    
    return redirect(url_for('exam'))

@app.route('/exam')
def exam():
    """Main exam page that loads all questions"""
    # Validate session
    if not validate_session():
        return redirect(url_for('index'))

    if not session.get('exam_started'):
        # If no exam is started, automatically start one
        all_questions = load_questions()
        exam_seed = random.randint(1, 1000000)
        session['exam_started'] = True
        session['answers'] = {}
        session['total_questions'] = len(all_questions.get('list1', []))
        session['exam_seed'] = exam_seed
        session['randomize_questions'] = True  # Default to true
        session['question_list'] = 'list1'

    all_questions = load_questions()
    exam_seed = session.get('exam_seed')
    randomize_questions = session.get('randomize_questions', True)
    question_list_key = session.get('question_list', 'list1')
    if question_list_key == 'random120':
        questions = get_all_questions_for_random120()
        random.seed(exam_seed)
        questions = random.sample(questions, min(120, len(questions)))
    elif question_list_key == 'all_questions':
        questions = get_all_questions()
    else:
        questions = all_questions.get(question_list_key, [])

    randomized_questions = randomize_questions_and_options(
        questions,
        exam_seed,
        randomize_questions
    )

    return render_template('exam.html',
                         questions=randomized_questions,
                         total_questions=len(randomized_questions),
                         randomize_questions=randomize_questions)

@app.route('/update_randomization', methods=['POST'])
def update_randomization():
    """Update randomization settings"""
    if not validate_session():
        return jsonify({'error': 'Invalid session'}), 400

    if not session.get('exam_started'):
        return jsonify({'error': 'No exam started'}), 400

    data = request.json
    room_code = request.args.get('room_code')
    if room_code and room_code in GAMES:
        GAMES[room_code]['randomize_questions'] = data.get('randomize_questions', True)
    else:
        session['randomize_questions'] = data.get('randomize_questions', True)

    return jsonify({'success': True})

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    """Handle final exam submission"""
    if not validate_session():
        return jsonify({'error': 'Invalid session'}), 400

    if not session.get('exam_started'):
        return jsonify({'error': 'No exam started'}), 400

    # Check if exam was already submitted
    if session.get('exam_submitted'):
        return jsonify({'error': 'Exam already submitted'}), 400

    # Get answers from request
    answers = request.json.get('answers', {})

    # Validate answers format
    if not isinstance(answers, dict):
        return jsonify({'error': 'Invalid answers format'}), 400

    # Regenerate questions using the same seed and settings for consistent scoring
    all_questions = load_questions()
    exam_seed = session.get('exam_seed')
    randomize_questions = session.get('randomize_questions', True)
    question_list_key = session.get('question_list', 'list1')
    questions = all_questions.get(question_list_key, [])

    if not exam_seed:
        return jsonify({'error': 'Invalid exam session'}), 400

    randomized_questions = randomize_questions_and_options(
        questions,
        exam_seed,
        randomize_questions
    )

    correct_answers = 0
    total_questions = len(randomized_questions)

    # Score the exam (robust to key and type issues)
    for idx, question in enumerate(randomized_questions):
        user_answer = answers.get(str(idx))
        if user_answer is None:
            user_answer = answers.get(idx)
        if user_answer is not None:
            try:
                if int(user_answer) == int(question['correct_answer']):
                    correct_answers += 1
            except Exception:
                pass

    score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    # Mark exam as submitted to prevent duplicate submissions
    session['exam_submitted'] = True

    # Store results in session for potential review
    session['exam_results'] = {
        'session_id': session.get('session_id'),
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'score_percentage': score_percentage,
        'answers': answers,
        'questions': randomized_questions,
        'submitted_at': datetime.now().isoformat()
    }

    return jsonify({
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'score_percentage': score_percentage
    })

@app.route('/results')
def results():
    """Show exam results page"""
    if not validate_session():
        return redirect(url_for('index'))
    
    if not session.get('exam_submitted') or not session.get('exam_results'):
        return redirect(url_for('index'))
    
    # Validate that results belong to current session
    results = session.get('exam_results')
    if results.get('session_id') != session.get('session_id'):
        return redirect(url_for('index'))
    
    return render_template('results.html',
                         correct_answers=results['correct_answers'],
                         total_questions=results['total_questions'],
                         score_percentage=results['score_percentage'])

@app.route('/restart')
def restart():
    """Restart the exam"""
    # Create a completely new session
    create_new_session()
    return redirect(url_for('index'))

@app.route('/get_questions_data')
def get_questions_data():
    """Get questions data with current randomization settings"""
    if not validate_session():
        return jsonify({'error': 'Invalid session'}), 400

    if not session.get('exam_started'):
        return jsonify({'error': 'No exam started'}), 400

    room_code = request.args.get('room_code')
    if room_code and room_code in GAMES:
        game = GAMES[room_code]
        if game['question_list'] == 'random120':
            questions = get_all_questions_for_random120()
            exam_seed = game['seed']
            random.seed(exam_seed)
            questions = random.sample(questions, min(120, len(questions)))
        else:
            questions = load_questions().get(game['question_list'], [])
            exam_seed = game['seed']
        randomize_questions = game.get('randomize_questions', True)
    else:
        all_questions = load_questions()
        exam_seed = session.get('exam_seed')
        randomize_questions = session.get('randomize_questions', True)
        question_list_key = session.get('question_list', 'list1')
        if question_list_key == 'random120':
            questions = get_all_questions_for_random120()
            random.seed(exam_seed)
            questions = random.sample(questions, min(120, len(questions)))
        elif question_list_key == 'all_questions':
            questions = get_all_questions()
        else:
            questions = all_questions.get(question_list_key, [])

    if not exam_seed:
        return jsonify({'error': 'Invalid exam session'}), 400

    randomized_questions = randomize_questions_and_options(
        questions,
        exam_seed,
        randomize_questions
    )

    return jsonify({
        'questions': randomized_questions,
        'total_questions': len(randomized_questions),
        'randomize_questions': randomize_questions
    })

def generate_room_code(length=6):
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if code not in GAMES:
            return code

def get_all_questions_for_random120():
    questions = load_questions()
    all_questions = []
    for k in ['list1', 'list2', 'list3', 'list4', 'list5', 'list6']:
        all_questions.extend(questions.get(k, []))
    return all_questions

def get_all_questions():
    """Get all questions from all lists combined"""
    questions = load_questions()
    all_questions = []
    for k in ['list1', 'list2', 'list3', 'list4', 'list5', 'list6']:
        all_questions.extend(questions.get(k, []))
    return all_questions

@socketio.on('create_room')
def handle_create_room(data):
    name = data.get('name', 'مجهول')
    client_id = data.get('client_id')
    session_id = request.sid
    room_code = generate_room_code()
    question_list_key = data.get('question_list', 'list1')
    all_questions = load_questions()
    if question_list_key == 'random120':
        questions = get_all_questions_for_random120()
        seed = random.randint(1, 1000000)
        random.seed(seed)
        questions = random.sample(questions, min(120, len(questions)))
    elif question_list_key == 'all_questions':
        questions = get_all_questions()
        seed = random.randint(1, 1000000)
    else:
        if question_list_key not in all_questions:
            question_list_key = 'list1'
        questions = all_questions[question_list_key]
        seed = random.randint(1, 1000000)
    randomized_questions = randomize_questions_and_options(questions, seed, True)
    GAMES[room_code] = {
        'host': client_id,
        'players': {
            client_id: {'name': name, 'score': 0, 'time': 0, 'finished': False, 'sid': session_id}
        },
        'questions': randomized_questions,
        'started': False,
        'start_time': None,
        'end_time': None,
        'seed': seed,
        'question_list': question_list_key,
        'total_questions': len(randomized_questions)
    }
    join_room(room_code)
    emit('room_created', {'room_code': room_code, 'players': GAMES[room_code]['players'], 'question_list': question_list_key, 'total_questions': len(randomized_questions)}, room=session_id)

@socketio.on('join_room')
def handle_join_room(data):
    name = data.get('name', 'مجهول')
    room_code = data.get('room_code', '').upper().strip()
    client_id = data.get('client_id')
    session_id = request.sid
    question_list_key = data.get('question_list', None)
    if room_code not in GAMES:
        emit('error', {'message': 'رمز الغرفة غير صحيح.'}, room=session_id)
        return
    if GAMES[room_code]['started']:
        emit('error', {'message': 'الامتحان قد بدأ بالفعل، لا يمكن الانضمام الآن.'}, room=session_id)
        return
    if question_list_key and question_list_key == 'random120':
        # Only allow if the room was created with random120
        if GAMES[room_code]['question_list'] != 'random120':
            emit('error', {'message': 'قائمة الأسئلة لا تطابق الغرفة.'}, room=session_id)
            return
    elif question_list_key and question_list_key == 'all_questions':
        # Only allow if the room was created with all_questions
        if GAMES[room_code]['question_list'] != 'all_questions':
            emit('error', {'message': 'قائمة الأسئلة لا تطابق الغرفة.'}, room=session_id)
            return
    GAMES[room_code]['players'][client_id] = GAMES[room_code]['players'].get(client_id, {'name': name, 'score': 0, 'time': 0, 'finished': False})
    GAMES[room_code]['players'][client_id]['sid'] = session_id
    join_room(room_code)
    emit('player_joined', {'players': GAMES[room_code]['players'], 'question_list': GAMES[room_code]['question_list'], 'total_questions': GAMES[room_code]['total_questions']}, room=room_code)

@socketio.on('start_game')
def handle_start_game(data):
    room_code = data.get('room_code')
    client_id = data.get('client_id')
    session_id = request.sid
    if room_code not in GAMES or GAMES[room_code]['host'] != client_id:
        emit('error', {'message': 'غير مصرح لك ببدء الامتحان.'}, room=session_id)
        return
    GAMES[room_code]['started'] = True
    GAMES[room_code]['start_time'] = datetime.now().isoformat()
    emit('game_started', {
        'questions': GAMES[room_code]['questions'],
        'start_time': GAMES[room_code]['start_time'],
        'question_list': GAMES[room_code]['question_list'],
        'total_questions': GAMES[room_code]['total_questions']
    }, room=room_code)

@socketio.on('progress_update')
def handle_progress_update(data):
    room_code = data.get('room_code')
    current_index = data.get('current_index', 0)
    client_id = data.get('client_id')
    session_id = request.sid
    if room_code not in GAMES or client_id not in GAMES[room_code]['players']:
        return
    GAMES[room_code]['players'][client_id]['progress'] = current_index
    # Broadcast updated leaderboard
    leaderboard = [
        {
            'name': p['name'],
            'score': p['score'],
            'time': p['time'],
            'finished': p['finished'],
            'progress': p.get('progress', 0)
        }
        for p in GAMES[room_code]['players'].values()
    ]
    leaderboard.sort(key=lambda x: (-x['score'], x['time']))
    emit('leaderboard_update', {'leaderboard': leaderboard}, room=room_code)

@socketio.on('submit_answers')
def handle_submit_answers(data):
    room_code = data.get('room_code')
    answers = data.get('answers', {})
    client_id = data.get('client_id')
    session_id = request.sid

    if room_code not in GAMES or client_id not in GAMES[room_code]['players']:
        emit('error', {'message': 'حدث خطأ في إرسال الإجابات.'}, room=session_id)
        return
    player = GAMES[room_code]['players'][client_id]
    if player.get('submitted'):
        emit('error', {'message': 'لقد أرسلت إجاباتك بالفعل.'}, room=session_id)
        return
    questions = GAMES[room_code]['questions']
    correct = 0
    for idx, q in enumerate(questions):
        user_answer = answers.get(str(idx))
        if user_answer is not None and int(user_answer) == int(q['correct_answer']):
            correct += 1
    finish_time = (datetime.now() - datetime.fromisoformat(GAMES[room_code]['start_time'])).total_seconds()
    player['score'] = correct
    player['time'] = finish_time
    player['finished'] = True
    player['progress'] = len(questions)
    player['submitted'] = True
    # Broadcast leaderboard update
    leaderboard = [
        {
            'name': p['name'],
            'score': p['score'],
            'time': p['time'],
            'finished': p['finished'],
            'progress': p.get('progress', 0)
        }
        for p in GAMES[room_code]['players'].values()
    ]
    leaderboard.sort(key=lambda x: (-x['score'], x['time']))
    emit('leaderboard_update', {'leaderboard': leaderboard, 'total_questions': GAMES[room_code]['total_questions']}, room=room_code)

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    # Remove player from all rooms
    for room_code, game in list(GAMES.items()):
        if session_id in game['players']:
            leave_room(room_code)
            del game['players'][session_id]
            # If host left, assign new host or delete game if empty
            if game['host'] == session_id:
                if game['players']:
                    game['host'] = next(iter(game['players']))
                else:
                    del GAMES[room_code]
                    continue
            emit('player_left', {'players': game['players']}, room=room_code)

@app.route('/sound/correct')
def sound_correct():
    return send_file(BytesIO(CORRECT_SOUND), mimetype='audio/mpeg', as_attachment=False, download_name='correct.mp3')

@app.route('/sound/wrong')
def sound_wrong():
    return send_file(BytesIO(WRONG_SOUND), mimetype='audio/mpeg', as_attachment=False, download_name='wrong.mp3')

@app.route('/sound/toggle')
def sound_toggle():
    return send_file(BytesIO(TOGGLE_SOUND), mimetype='audio/mpeg', as_attachment=False, download_name='toggle.mp3')

# Ensure static files are served (Flask does this by default from /static)
# If you want to customize, uncomment below:
# from flask import send_from_directory
# @app.route('/static/<path:filename>')
# def static_files(filename):
#     return send_from_directory('static', filename)

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
