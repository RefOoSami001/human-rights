from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import random
import uuid
import string
from datetime import datetime, timedelta
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production-' + uuid.uuid4().hex)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------
QUESTIONS: dict | None = None

GAMES: dict = {}
# Structure:
# {
#   room_code: {
#     'host': client_id,
#     'players': { client_id: { name, score, time, finished, progress, sid, submitted } },
#     'questions': [...],
#     'started': bool,
#     'start_time': ISO str | None,
#     'seed': int,
#     'question_list': str,
#     'total_questions': int,
#   }
# }

# ---------------------------------------------------------------------------
# Question helpers
# ---------------------------------------------------------------------------

def load_questions() -> dict:
    global QUESTIONS
    if QUESTIONS is None:
        path = os.path.join(os.path.dirname(__file__), 'questions.json')
        with open(path, 'r', encoding='utf-8') as f:
            QUESTIONS = json.load(f)
    return QUESTIONS


def get_available_question_lists() -> dict:
    questions = load_questions()
    return {k: len(v) for k, v in questions.items() if isinstance(v, list)}


def get_all_questions_for_random120() -> list:
    questions = load_questions()
    result = []
    for k in ['list1', 'list2', 'list3', 'list4', 'list5', 'list6']:
        result.extend(questions.get(k, []))
    return result


def get_all_questions() -> list:
    questions = load_questions()
    result = []
    for k in ['list1', 'list2', 'list3', 'list4', 'list5', 'list6']:
        result.extend(questions.get(k, []))
    return result


def resolve_question_list(key: str, seed: int) -> list:
    """Return the raw (un-shuffled) question list for a given key."""
    all_q = load_questions()
    if key == 'random120':
        pool = get_all_questions_for_random120()
        rng = random.Random(seed)
        return rng.sample(pool, min(120, len(pool)))
    if key == 'all_questions':
        return get_all_questions()
    return all_q.get(key, all_q.get('list1', []))


def randomize_questions_and_options(questions: list, seed: int, shuffle_order: bool = True) -> list:
    """Shuffle options (tracking correct answer) and optionally shuffle question order."""
    rng = random.Random(seed)
    result = []
    for q in questions:
        nq = q.copy()
        opts = list(q['options'])
        correct_idx = int(q['correct_answer'])
        indices = list(range(len(opts)))
        rng.shuffle(indices)
        nq['options'] = [opts[i] for i in indices]
        nq['correct_answer'] = indices.index(correct_idx)
        result.append(nq)
    if shuffle_order:
        rng.shuffle(result)
    return result


def generate_room_code() -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if code not in GAMES:
            return code

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _generate_session_id() -> str:
    return str(uuid.uuid4())


def validate_session() -> bool:
    if not session.get('session_id'):
        return False
    created = session.get('session_created')
    if created:
        try:
            if datetime.now() - datetime.fromisoformat(created) > timedelta(hours=24):
                return False
        except Exception:
            return False
    return True


def create_new_session():
    session.clear()
    session['session_id'] = _generate_session_id()
    session['session_created'] = datetime.now().isoformat()
    session['exam_started'] = False
    session['exam_submitted'] = False
    session['answers'] = {}
    session['total_questions'] = 0
    session['exam_seed'] = None
    session['randomize_questions'] = True
    session['question_list'] = 'list1'

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if not validate_session():
        create_new_session()
    return render_template('index.html')


@app.route('/start_exam', methods=['GET', 'POST'])
def start_exam():
    if not validate_session():
        create_new_session()

    question_list_key = request.args.get('list', 'list1')
    seed = random.randint(1, 1_000_000)
    raw_questions = resolve_question_list(question_list_key, seed)

    session['exam_started'] = True
    session['exam_submitted'] = False
    session['answers'] = {}
    session['exam_seed'] = seed
    session['randomize_questions'] = True
    session['question_list'] = question_list_key
    session['total_questions'] = len(raw_questions)

    return redirect(url_for('exam'))


@app.route('/exam')
def exam():
    if not validate_session():
        return redirect(url_for('index'))

    if not session.get('exam_started'):
        return redirect(url_for('index'))

    seed = session['exam_seed']
    key = session.get('question_list', 'list1')
    shuffle = session.get('randomize_questions', True)

    raw = resolve_question_list(key, seed)
    questions = randomize_questions_and_options(raw, seed, shuffle)

    return render_template(
        'exam.html',
        questions=questions,
        total_questions=len(questions),
        randomize_questions=shuffle,
    )


@app.route('/get_question_lists')
def get_question_lists():
    return jsonify(get_available_question_lists())


@app.route('/get_questions_data')
def get_questions_data():
    if not validate_session():
        return jsonify({'error': 'Invalid session'}), 400
    if not session.get('exam_started'):
        return jsonify({'error': 'No exam started'}), 400

    seed = session.get('exam_seed')
    if not seed:
        return jsonify({'error': 'Invalid exam session'}), 400

    key = session.get('question_list', 'list1')
    shuffle = session.get('randomize_questions', True)
    raw = resolve_question_list(key, seed)
    questions = randomize_questions_and_options(raw, seed, shuffle)

    return jsonify({
        'questions': questions,
        'total_questions': len(questions),
        'randomize_questions': shuffle,
    })


@app.route('/update_randomization', methods=['POST'])
def update_randomization():
    if not validate_session():
        return jsonify({'error': 'Invalid session'}), 400
    if not session.get('exam_started'):
        return jsonify({'error': 'No exam started'}), 400

    data = request.get_json(silent=True) or {}
    session['randomize_questions'] = bool(data.get('randomize_questions', True))
    return jsonify({'success': True})


@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    if not validate_session():
        return jsonify({'error': 'Invalid session'}), 400
    if not session.get('exam_started'):
        return jsonify({'error': 'No exam started'}), 400
    if session.get('exam_submitted'):
        return jsonify({'error': 'Exam already submitted'}), 400

    data = request.get_json(silent=True) or {}
    answers = data.get('answers', {})
    if not isinstance(answers, dict):
        return jsonify({'error': 'Invalid answers format'}), 400

    seed = session.get('exam_seed')
    if not seed:
        return jsonify({'error': 'Invalid exam session'}), 400

    key = session.get('question_list', 'list1')
    shuffle = session.get('randomize_questions', True)
    raw = resolve_question_list(key, seed)
    questions = randomize_questions_and_options(raw, seed, shuffle)

    correct = 0
    for idx, q in enumerate(questions):
        user_ans = answers.get(str(idx), answers.get(idx))
        if user_ans is not None:
            try:
                if int(user_ans) == int(q['correct_answer']):
                    correct += 1
            except (ValueError, TypeError):
                pass

    total = len(questions)
    pct = (correct / total * 100) if total > 0 else 0

    session['exam_submitted'] = True
    session['exam_results'] = {
        'session_id': session['session_id'],
        'correct_answers': correct,
        'total_questions': total,
        'score_percentage': pct,
        'answers': answers,
        'questions': questions,
        'submitted_at': datetime.now().isoformat(),
    }

    return jsonify({
        'correct_answers': correct,
        'total_questions': total,
        'score_percentage': pct,
    })


@app.route('/results')
def results():
    if not validate_session():
        return redirect(url_for('index'))
    if not session.get('exam_submitted') or not session.get('exam_results'):
        return redirect(url_for('index'))

    res = session['exam_results']
    if res.get('session_id') != session.get('session_id'):
        return redirect(url_for('index'))

    return render_template(
        'results.html',
        correct_answers=res['correct_answers'],
        total_questions=res['total_questions'],
        score_percentage=res['score_percentage'],
    )


@app.route('/restart')
def restart():
    create_new_session()
    return redirect(url_for('index'))

# ---------------------------------------------------------------------------
# Socket.IO events
# ---------------------------------------------------------------------------

@socketio.on('create_room')
def handle_create_room(data):
    name = (data.get('name') or 'مجهول').strip()
    client_id = data.get('client_id')
    sid = request.sid
    key = data.get('question_list', 'list1')

    seed = random.randint(1, 1_000_000)
    raw = resolve_question_list(key, seed)
    questions = randomize_questions_and_options(raw, seed, True)
    room_code = generate_room_code()

    GAMES[room_code] = {
        'host': client_id,
        'players': {
            client_id: {
                'name': name, 'score': 0, 'time': 0,
                'finished': False, 'progress': 0,
                'submitted': False, 'sid': sid,
            }
        },
        'questions': questions,
        'started': False,
        'start_time': None,
        'seed': seed,
        'question_list': key,
        'total_questions': len(questions),
    }
    join_room(room_code)
    emit('room_created', {
        'room_code': room_code,
        'players': _safe_players(GAMES[room_code]['players']),
        'question_list': key,
        'total_questions': len(questions),
    }, to=sid)


@socketio.on('join_room')
def handle_join_room(data):
    name = (data.get('name') or 'مجهول').strip()
    room_code = (data.get('room_code') or '').upper().strip()
    client_id = data.get('client_id')
    sid = request.sid

    if room_code not in GAMES:
        emit('error', {'message': 'رمز الغرفة غير صحيح.'}, to=sid)
        return
    game = GAMES[room_code]
    if game['started']:
        emit('error', {'message': 'الامتحان قد بدأ بالفعل، لا يمكن الانضمام الآن.'}, to=sid)
        return

    if client_id not in game['players']:
        game['players'][client_id] = {
            'name': name, 'score': 0, 'time': 0,
            'finished': False, 'progress': 0,
            'submitted': False,
        }
    game['players'][client_id]['sid'] = sid

    join_room(room_code)
    emit('player_joined', {
        'players': _safe_players(game['players']),
        'question_list': game['question_list'],
        'total_questions': game['total_questions'],
    }, to=room_code)


@socketio.on('start_game')
def handle_start_game(data):
    room_code = data.get('room_code')
    client_id = data.get('client_id')
    sid = request.sid

    if room_code not in GAMES:
        emit('error', {'message': 'الغرفة غير موجودة.'}, to=sid)
        return
    game = GAMES[room_code]
    if game['host'] != client_id:
        emit('error', {'message': 'غير مصرح لك ببدء الامتحان.'}, to=sid)
        return

    game['started'] = True
    game['start_time'] = datetime.now().isoformat()

    emit('game_started', {
        'questions': game['questions'],
        'start_time': game['start_time'],
        'question_list': game['question_list'],
        'total_questions': game['total_questions'],
    }, to=room_code)


@socketio.on('progress_update')
def handle_progress_update(data):
    room_code = data.get('room_code')
    client_id = data.get('client_id')
    current_index = int(data.get('current_index', 0))

    if room_code not in GAMES or client_id not in GAMES[room_code]['players']:
        return

    GAMES[room_code]['players'][client_id]['progress'] = current_index
    _broadcast_leaderboard(room_code)


@socketio.on('submit_answers')
def handle_submit_answers(data):
    room_code = data.get('room_code')
    client_id = data.get('client_id')
    answers = data.get('answers', {})
    sid = request.sid

    if room_code not in GAMES or client_id not in GAMES[room_code]['players']:
        emit('error', {'message': 'حدث خطأ في إرسال الإجابات.'}, to=sid)
        return

    game = GAMES[room_code]
    player = game['players'][client_id]

    if player.get('submitted'):
        return  # silently ignore duplicate submissions

    questions = game['questions']
    correct = 0
    for idx, q in enumerate(questions):
        user_ans = answers.get(str(idx))
        if user_ans is not None:
            try:
                if int(user_ans) == int(q['correct_answer']):
                    correct += 1
            except (ValueError, TypeError):
                pass

    elapsed = 0.0
    if game['start_time']:
        elapsed = (datetime.now() - datetime.fromisoformat(game['start_time'])).total_seconds()

    player.update({
        'score': correct,
        'time': round(elapsed, 1),
        'finished': True,
        'progress': len(questions),
        'submitted': True,
    })

    _broadcast_leaderboard(room_code, include_total=True)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for room_code, game in list(GAMES.items()):
        # Find the player with this sid
        cid = next(
            (c for c, p in game['players'].items() if p.get('sid') == sid),
            None,
        )
        if cid is None:
            continue

        leave_room(room_code)
        del game['players'][cid]

        if not game['players']:
            del GAMES[room_code]
            continue

        # Re-assign host if needed
        if game['host'] == cid:
            game['host'] = next(iter(game['players']))

        emit('player_left', {
            'players': _safe_players(game['players']),
            'question_list': game['question_list'],
            'total_questions': game['total_questions'],
        }, to=room_code)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_players(players: dict) -> dict:
    """Return players dict without the internal 'sid' key."""
    return {
        cid: {k: v for k, v in p.items() if k != 'sid'}
        for cid, p in players.items()
    }


def _broadcast_leaderboard(room_code: str, include_total: bool = False):
    game = GAMES[room_code]
    lb = sorted(
        [
            {
                'name': p['name'],
                'score': p['score'],
                'time': p['time'],
                'finished': p['finished'],
                'progress': p.get('progress', 0),
            }
            for p in game['players'].values()
        ],
        key=lambda x: (-x['score'], x['time']),
    )
    payload: dict = {'leaderboard': lb}
    if include_total:
        payload['total_questions'] = game['total_questions']
    emit('leaderboard_update', payload, to=room_code)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
