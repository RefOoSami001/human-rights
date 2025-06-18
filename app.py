from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import random

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

def randomize_questions_and_options(questions, seed=None, randomize_questions=True, randomize_options=True):
    """Randomize questions and options while maintaining correct answer tracking"""
    if seed is not None:
        random.seed(seed)
    
    randomized_questions = []
    
    for question in questions:
        # Create a copy of the question
        new_question = question.copy()
        
        # Get original options and correct answer
        original_options = question['options']
        original_correct = question['correct_answer']
        
        if randomize_options:
            # Create list of option indices
            option_indices = list(range(len(original_options)))
            
            # Randomize option order
            random.shuffle(option_indices)
            
            # Create new options list with randomized order
            new_options = [original_options[i] for i in option_indices]
            
            # Find the new index of the correct answer
            new_correct_index = option_indices.index(original_correct)
            
            # Update question with randomized options and correct answer
            new_question['options'] = new_options
            new_question['correct_answer'] = new_correct_index
        else:
            # Keep original options order
            new_question['options'] = original_options
            new_question['correct_answer'] = original_correct
        
        randomized_questions.append(new_question)
    
    # Randomize question order if requested
    if randomize_questions:
        random.shuffle(randomized_questions)
    
    return randomized_questions

@app.route('/')
def index():
    """Root page - automatically start exam and redirect to exam page"""
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
    session['randomize_options'] = True    # Default to true
    
    return redirect(url_for('exam'))

@app.route('/start_exam')
def start_exam():
    """Initialize exam session and redirect to exam page"""
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
    session['randomize_options'] = True    # Default to true
    
    return redirect(url_for('exam'))

@app.route('/exam')
def exam():
    """Main exam page that loads all questions"""
    if not session.get('exam_started'):
        # If no exam is started, automatically start one
        questions = load_questions()
        exam_seed = random.randint(1, 1000000)
        session['exam_started'] = True
        session['answers'] = {}
        session['total_questions'] = len(questions)
        session['exam_seed'] = exam_seed
        session['randomize_questions'] = True  # Default to true
        session['randomize_options'] = True    # Default to true
    
    # Load and randomize questions using the stored seed and settings
    questions = load_questions()
    exam_seed = session.get('exam_seed')
    randomize_questions = session.get('randomize_questions', True)
    randomize_options = session.get('randomize_options', True)
    
    randomized_questions = randomize_questions_and_options(
        questions, 
        exam_seed, 
        randomize_questions, 
        randomize_options
    )
    
    return render_template('exam.html', 
                         questions=randomized_questions,
                         total_questions=len(randomized_questions),
                         randomize_questions=randomize_questions,
                         randomize_options=randomize_options)

@app.route('/update_randomization', methods=['POST'])
def update_randomization():
    """Update randomization settings"""
    if not session.get('exam_started'):
        return jsonify({'error': 'No exam started'}), 400
    
    data = request.json
    session['randomize_questions'] = data.get('randomize_questions', True)
    session['randomize_options'] = data.get('randomize_options', True)
    
    return jsonify({'success': True})

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    """Handle final exam submission"""
    if not session.get('exam_started'):
        return redirect(url_for('index'))
    
    # Get answers from request
    answers = request.json.get('answers', {})
    
    # Regenerate questions using the same seed and settings for consistent scoring
    questions = load_questions()
    exam_seed = session.get('exam_seed')
    randomize_questions = session.get('randomize_questions', True)
    randomize_options = session.get('randomize_options', True)
    
    randomized_questions = randomize_questions_and_options(
        questions, 
        exam_seed, 
        randomize_questions, 
        randomize_options
    )
    
    correct_answers = 0
    total_questions = len(randomized_questions)
    
    for i, question in enumerate(randomized_questions, 1):
        user_answer = answers.get(str(i))
        if user_answer is not None and user_answer == question['correct_answer']:
            correct_answers += 1
    
    score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # Clear session
    session.clear()
    
    return jsonify({
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'score_percentage': score_percentage
    })

@app.route('/restart')
def restart():
    """Restart the exam"""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)
