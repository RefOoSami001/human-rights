# بنك طب نساء — MCQ Exam App

A professional Flask-based multiple-choice exam application with real-time multiplayer support.

## Features

- **Solo mode** — start an exam with any question list, immediate answer feedback
- **Multiplayer mode** — create or join a room via Socket.IO, live leaderboard
- **Question randomization** — shuffle both question order and option order
- **Review wrong answers** — detailed review in the results modal
- **RTL Arabic UI** — clean, modern design built with Bootstrap 5 + Alexandria font
- **Keyboard shortcuts** — press 1–5 to answer, ← → to navigate

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run (development)
python app.py

# 3. Open http://localhost:5000
```

## Production Deployment

```bash
# Render / Railway / Heroku
gunicorn --worker-class eventlet -w 1 app:app
```

Set the `SECRET_KEY` environment variable to a long random string before deploying.

## Project Structure

```
├── app.py                  # Flask application + Socket.IO handlers
├── questions.json          # MCQ data (lists: list1–list6)
├── templates/
│   ├── base.html           # Shared layout, CSS, fonts
│   ├── index.html          # Landing / question-list picker
│   ├── exam.html           # Exam + multiplayer lobby
│   └── results.html        # Standalone results page
├── convert_questions.py    # Utility: convert text → questions.json
├── requirements.txt
├── Procfile
└── runtime.txt
```

## Adding Questions

Edit `questions.json`. Each list is an array of objects:

```json
{
  "list1": [
    {
      "number": 1,
      "text": "Question text here",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": 0
    }
  ]
}
```

Alternatively, use `convert_questions.py` to convert a formatted text file.

## Environment Variables

| Variable     | Default                        | Description                    |
|--------------|--------------------------------|--------------------------------|
| `SECRET_KEY` | random (change in production!) | Flask session secret           |
| `PORT`       | `5000`                         | Port to listen on              |

## Author

**Raafat Sami** — صُنع بـ ❤️
