from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import random
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Global variable to store questions (loaded once)
QUESTIONS = None

# Load questions from JSON file
def load_questions():
    global QUESTIONS
    if QUESTIONS is None:
        with open('questions.json', 'r', encoding='utf-8') as file:
            QUESTIONS = json.load(file)
    return QUESTIONS

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
    """Randomize questions while maintaining correct answer tracking"""
    if seed is not None:
        random.seed(seed)
    
    randomized_questions = []
    
    for question in questions:
        # Create a copy of the question
        new_question = question.copy()
        
        # Keep original options and correct answer (no option randomization)
        new_question['options'] = question['options']
        new_question['correct_answer'] = question['correct_answer']
        
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
        questions = load_questions()
        exam_seed = random.randint(1, 1000000)
        session['exam_started'] = True
        session['answers'] = {}
        session['total_questions'] = len(questions)
        session['exam_seed'] = exam_seed
        session['randomize_questions'] = True  # Default to true
    
    # Load and randomize questions using the stored seed and settings
    questions = load_questions()
    exam_seed = session.get('exam_seed')
    randomize_questions = session.get('randomize_questions', True)
    
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
    questions = load_questions()
    exam_seed = session.get('exam_seed')
    randomize_questions = session.get('randomize_questions', True)
    
    if not exam_seed:
        return jsonify({'error': 'Invalid exam session'}), 400
    
    randomized_questions = randomize_questions_and_options(
        questions, 
        exam_seed, 
        randomize_questions
    )
    
    correct_answers = 0
    total_questions = len(randomized_questions)
    
    # Score the exam
    for i, question in enumerate(randomized_questions, 1):
        user_answer = answers.get(str(i))
        if user_answer is not None and user_answer == question['correct_answer']:
            correct_answers += 1
    
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
    
    # Load and randomize questions using the stored seed and settings
    questions = load_questions()
    exam_seed = session.get('exam_seed')
    randomize_questions = session.get('randomize_questions', True)
    
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

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)
