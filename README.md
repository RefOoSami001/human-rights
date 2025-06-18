# Human Rights MCQ Exam Application

A modern, responsive web application for conducting multiple-choice question (MCQ) exams with advanced features and user-friendly interface.

## 🌟 Features

### Core Functionality
- **Interactive MCQ Exam**: Dynamic question loading with immediate feedback
- **Question Randomization**: Optional randomization of question order for fair testing
- **Progress Tracking**: Real-time progress bar and question navigation
- **Results Analysis**: Detailed score breakdown and performance feedback
- **Review System**: Review incorrect answers with correct solutions

### User Experience
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **RTL Support**: Full Arabic language support with right-to-left layout
- **Modern UI**: Clean, intuitive interface with smooth animations
- **Keyboard Navigation**: Support for keyboard shortcuts and navigation
- **Touch-Friendly**: Optimized for touch devices with swipe gestures

### Technical Features
- **Session Management**: Secure user session handling with unique IDs
- **Multi-User Support**: Concurrent user support without conflicts
- **Session Expiration**: Automatic session cleanup (24-hour expiry)
- **Data Validation**: Comprehensive input validation and error handling
- **Performance Optimized**: Efficient question loading and rendering

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Flask framework

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/RefOoSami001/human-rights.git
   cd human-rights
   ```

2. **Install dependencies**
   ```bash
   pip install flask
   ```

3. **Prepare questions data**
   - Ensure `questions.json` file exists with proper MCQ format
   - Questions should follow this structure:
   ```json
   [
     {
       "text": "Question text here",
       "options": ["Option A", "Option B", "Option C", "Option D"],
       "correct_answer": 0
     }
   ]
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - The exam will start automatically

## 📁 Project Structure

```
MCQ/
├── app.py                 # Main Flask application
├── questions.json         # MCQ questions data
├── templates/
│   ├── base.html         # Base template with common elements
│   ├── exam.html         # Main exam interface
│   └── results.html      # Results display page
└── README.md             # Project documentation
```

## 🎯 Usage

### For Students
1. **Start Exam**: Visit the application URL to begin
2. **Answer Questions**: Click on options or use keyboard (1-4)
3. **Navigate**: Use Previous/Next buttons or swipe on mobile
4. **Submit**: Click "Finish Exam" when complete
5. **Review Results**: View score and review incorrect answers

### For Administrators
1. **Update Questions**: Modify `questions.json` file
2. **Customize Settings**: Adjust randomization defaults in `app.py`
3. **Deploy**: Use any Python hosting service (Heroku, PythonAnywhere, etc.)

## 🔧 Configuration

### Environment Variables
- `PORT`: Server port (default: 5000)
- `SECRET_KEY`: Flask secret key for session security

### Customization Options
- **Question Randomization**: Toggle in exam interface
- **Session Duration**: Modify in `validate_session()` function
- **UI Styling**: Customize CSS in `templates/base.html`

## 🛡️ Security Features

- **Session Isolation**: Each user gets unique session ID
- **Session Validation**: All requests validated for session integrity
- **Input Validation**: Comprehensive validation of user inputs
- **CSRF Protection**: Built-in Flask CSRF protection
- **Session Expiration**: Automatic cleanup of expired sessions

## 📱 Mobile Support

- **Responsive Design**: Adapts to all screen sizes
- **Touch Gestures**: Swipe navigation between questions
- **Touch-Friendly UI**: Large buttons and touch targets
- **Mobile-Optimized**: Reduced animations and optimized performance

## 🌐 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
1. **Set environment variables**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=your-secure-secret-key
   ```

2. **Use production server**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Hosting Platforms
- **Heroku**: Add `gunicorn` to requirements.txt
- **PythonAnywhere**: Upload files and configure WSGI
- **VPS**: Use nginx + gunicorn setup

## 🔄 Recent Updates

### Version 2.0
- ✅ Enhanced session management with unique user IDs
- ✅ Removed sound effects for better performance
- ✅ Fixed UI issues and improved responsive design
- ✅ Added comprehensive error handling
- ✅ Improved multi-user support
- ✅ Added session expiration and cleanup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

**RefOo** - [GitHub Profile](https://github.com/RefOoSami001)

## 🙏 Acknowledgments

- Flask framework for the web framework
- Bootstrap for responsive design components
- Font Awesome for icons
- Alexandria font for Arabic typography

---

**Note**: This application is designed for educational purposes and can be customized for various MCQ exam scenarios. 