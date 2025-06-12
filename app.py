from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
from werkzeug.utils import secure_filename
import logging
import random
import string
import time
from quiz_generator import generate_quiz
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='Templates')
app.secret_key = 'aica2'
app.debug = True

# Configure upload settings
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'doc', 'ppt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
	os.makedirs(UPLOAD_FOLDER)

# Store generated quizzes and users (in a real app, this would be in a database)
quizzes = {}
users = {}

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_quiz_code():
	"""Generate a unique 8-character quiz code"""
	while True:
		code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
		if code not in quizzes:
			return code

def generate_sample_questions(file_content, num_questions=5):
	"""Generate sample questions (placeholder for actual generation logic)"""
	questions = [
		{
			'question': f'Sample Question {i+1} from the document?',
			'options': [
				f'Option A for question {i+1}',
				f'Option B for question {i+1}',
				f'Option C for question {i+1}',
				f'Option D for question {i+1}'
			],
			'correct': random.randint(0, 3)
		}
		for i in range(num_questions)
	]
	return questions

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/test')
def test():
	return """
	<html>
		<body>
			<h1>Direct HTML Test</h1>
			<p>This is a direct HTML response without template rendering.</p>
		</body>
	</html>
	"""

@app.route('/select-role', methods=['GET', 'POST'])
def select_role():
	if request.method == 'POST':
		role = request.form.get('role')
		if role == 'teacher':
			return redirect(url_for('teacher_login'))
		elif role == 'student':
			return redirect(url_for('student_dashboard'))
	return render_template('select_role.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		username = request.form.get('username')
		password = request.form.get('password')
		email = request.form.get('email')
		
		if username in users:
			flash('Username already exists', 'error')
			return redirect(url_for('register'))
		
		users[username] = {
			'password': generate_password_hash(password),
			'email': email
		}
		
		flash('Registration successful! Please login.', 'success')
		return redirect(url_for('teacher_login'))
	
	return render_template('register.html')

@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
	if request.method == 'POST':
		username = request.form.get('username')
		password = request.form.get('password')
		
		if username in users and check_password_hash(users[username]['password'], password):
			session['teacher_logged_in'] = True
			session['teacher_username'] = username
			return redirect(url_for('teacher_dashboard'))
		else:
			flash('Invalid username or password', 'error')
	
	return render_template('teacher_login.html')

@app.route('/teacher/logout')
def teacher_logout():
	session.clear()
	return redirect(url_for('teacher_login'))

@app.route('/teacher/dashboard')
def teacher_dashboard():
	if not session.get('teacher_logged_in'):
		return redirect(url_for('teacher_login'))
	return render_template('teacher_dashboard.html', username=session.get('teacher_username'))

@app.route('/teacher-upload', methods=['GET', 'POST'])
def teacher_upload():
	if not session.get('teacher_logged_in'):
		return redirect(url_for('teacher_login'))
		
	if request.method == 'POST':
		if 'file' not in request.files:
			flash('No file selected')
			return redirect(request.url)
		
		file = request.files['file']
		if file.filename == '':
			flash('No file selected')
			return redirect(request.url)
		
		if file and allowed_file(file.filename):
			try:
				num_questions = min(int(request.form.get('num_questions', 10)), 20)
				quiz_type = request.form.get('quiz_type', 'mcq')
				quiz_code = generate_quiz_code()
				
				filename = secure_filename(f"{quiz_code}_{file.filename}")
				filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
				file.save(filepath)
				
				questions = generate_quiz(filepath, num_questions, quiz_type)
				
				if not questions:
					os.remove(filepath)
					flash('Could not generate questions from the document')
					return redirect(request.url)
				
				quizzes[quiz_code] = {
					'questions': questions,
					'filename': filename,
					'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
					'teacher': session.get('teacher_username'),
					'num_questions': len(questions),
					'quiz_type': quiz_type
				}
				
				return redirect(url_for('quiz_preview', quiz_code=quiz_code))
				
			except Exception as e:
				if os.path.exists(filepath):
					os.remove(filepath)
				flash(str(e))
				return redirect(request.url)
		else:
			flash('Invalid file type. Allowed types are: PDF, DOCX, PPT')
			return redirect(request.url)
			
	return render_template('teacher_upload.html')

@app.route('/teacher/create', methods=['GET', 'POST'])
def create_quiz():
	if request.method == 'POST':
		try:
			# Generate unique quiz code
			quiz_code = generate_quiz_code()
			
			# Get quiz data from form
			title = request.form.get('title')
			questions = []
			
			# Process each question from the form
			question_count = int(request.form.get('question_count', 0))
			for i in range(question_count):
				question = {
					'text': request.form.get(f'question_{i}'),
					'type': request.form.get(f'type_{i}'),
					'options': request.form.getlist(f'options_{i}[]') if request.form.get(f'type_{i}') == 'mcq' else None,
					'correct_answer': request.form.get(f'correct_{i}')
				}
				questions.append(question)
			
			# Here you would typically save to database
			# For now, just show success message
			flash(f'Quiz created successfully! Quiz Code: {quiz_code}', 'success')
			return redirect(url_for('teacher_dashboard'))
		except Exception as e:
			flash(f'Error creating quiz: {str(e)}', 'error')
			return redirect(request.url)
	
	return render_template('create_quiz.html')

@app.route('/student-dashboard')
def student_dashboard():
	return render_template('student_dashboard.html')

@app.route('/take-quiz', methods=['GET', 'POST'])
def take_quiz():
	if request.method == 'POST':
		quiz_code = request.form.get('quiz_code', '').strip().upper()
		if quiz_code in quizzes:
			# Store quiz code in session
			session['current_quiz'] = quiz_code
			return redirect(url_for('attempt_quiz', quiz_code=quiz_code))
		else:
			flash('Invalid quiz code. Please try again.')
			return redirect(url_for('student_dashboard'))
	return redirect(url_for('student_dashboard'))

@app.route('/attempt-quiz/<quiz_code>')
def attempt_quiz(quiz_code):
	# Check if quiz exists
	if quiz_code not in quizzes:
		flash('Quiz not found')
		return redirect(url_for('student_dashboard'))
	
	# Check if this is the quiz code stored in session
	if session.get('current_quiz') != quiz_code:
		flash('Please enter the quiz code first')
		return redirect(url_for('student_dashboard'))
	
	quiz_data = quizzes[quiz_code]
	
	# Create a copy of questions without correct answers for students
	student_questions = []
	for q in quiz_data['questions']:
		student_q = q.copy()
		if 'correct' in student_q:
			del student_q['correct']
		if 'correct_answer' in student_q:
			del student_q['correct_answer']
		student_questions.append(student_q)
	
	return render_template('attempt_quiz.html',
						 quiz_code=quiz_code,
						 questions=student_questions)

@app.route('/submit-quiz/<quiz_code>', methods=['POST'])
def submit_quiz(quiz_code):
	if quiz_code not in quizzes:
		flash('Quiz not found')
		return redirect(url_for('student_dashboard'))
	
	quiz_data = quizzes[quiz_code]
	questions = quiz_data['questions']
	student_name = request.form.get('student_name', '').strip()
	
	if not student_name:
		flash('Please enter your name')
		return redirect(url_for('attempt_quiz', quiz_code=quiz_code))
	
	# Process answers and calculate score
	score = 0
	total_questions = len(questions)
	answers = []
	
	for i, question in enumerate(questions):
		submitted = request.form.get(f'answer_{i}')
		
		if question['type'] == 'mcq':
			# For MCQ, compare the selected option index
			correct = question['correct']
			is_correct = submitted and int(submitted) == correct
			if is_correct:
				score += 1
			answers.append({
				'question': question['question'],
				'submitted': question['options'][int(submitted)] if submitted else None,
				'correct': question['options'][correct],
				'is_correct': is_correct
			})
		elif question['type'] == 'true_false':
			# For True/False, compare the boolean value
			correct = question['correct']
			is_correct = submitted and int(submitted) == correct
			if is_correct:
				score += 1
			answers.append({
				'question': question['question'],
				'submitted': 'True' if submitted == '0' else 'False',
				'correct': 'True' if correct == 0 else 'False',
				'is_correct': is_correct
			})
		elif question['type'] == 'fill_blanks':
			# For fill in the blanks, do case-insensitive comparison
			correct = question['options'][0]
			is_correct = submitted and submitted.lower().strip() == correct.lower().strip()
			if is_correct:
				score += 1
			answers.append({
				'question': question['question'],
				'submitted': submitted,
				'correct': correct,
				'is_correct': is_correct
			})
	
	# Calculate percentage
	percentage = (score / total_questions) * 100 if total_questions > 0 else 0
	
	# Store results in session
	session['last_quiz_results'] = {
		'student_name': student_name,
		'quiz_code': quiz_code,
		'score': score,
		'total': total_questions,
		'percentage': percentage,
		'answers': answers,
		'date': time.strftime('%Y-%m-%d %H:%M:%S')
	}
	
	# Add to quiz history
	if 'quiz_history' not in session:
		session['quiz_history'] = []
	session['quiz_history'].insert(0, {
		'code': quiz_code,
		'date': time.strftime('%Y-%m-%d %H:%M:%S'),
		'score': score,
		'total': total_questions,
		'percentage': percentage
	})
	
	# Clear current quiz from session
	session.pop('current_quiz', None)
	
	return redirect(url_for('quiz_result', quiz_id=quiz_code))

@app.route('/quiz-result/<quiz_id>')
def quiz_result(quiz_id):
	results = session.get('last_quiz_results')
	if not results or results['quiz_code'] != quiz_id:
		flash('Quiz results not found')
		return redirect(url_for('student_dashboard'))
	
	return render_template('quiz_results.html',
						 student_name=results['student_name'],
						 quiz_code=results['quiz_code'],
						 score=results['score'],
						 total=results['total'],
						 percentage=results['percentage'],
						 answers=results['answers'],
						 date=results['date'])

@app.route('/quiz-review/<quiz_id>')
def quiz_review(quiz_id):
	results = session.get('last_quiz_results')
	if not results or results['quiz_code'] != quiz_id:
		flash('Quiz results not found')
		return redirect(url_for('student_dashboard'))
	
	return render_template('quiz_review.html',
						 student_name=results['student_name'],
						 quiz_code=results['quiz_code'],
						 answers=results['answers'])

@app.route('/quiz-preview/<quiz_code>')
def quiz_preview(quiz_code):
	if quiz_code not in quizzes:
		flash('Quiz not found')
		return redirect(url_for('teacher_upload'))
	
	quiz_data = quizzes[quiz_code]
	return render_template('quiz_preview.html', 
						 quiz_code=quiz_code,
						 questions=quiz_data['questions'])

@app.route('/enter-quiz-code', methods=['GET', 'POST'])
def enter_quiz_code():
	if request.method == 'POST':
		quiz_code = request.form.get('quiz_code', '').strip().upper()
		if quiz_code in quizzes:
			return redirect(url_for('take_quiz', quiz_code=quiz_code))
		else:
			flash('Invalid quiz code. Please try again.')
			return redirect(url_for('enter_quiz_code'))
	return render_template('enter_quiz_code.html')

@app.route('/instructions')
def instructions():
	return render_template('instructions.html')

@app.route('/results')
def results():
	return render_template('results.html')

@app.route('/view-quiz/<quiz_id>')
def view_quiz(quiz_id):
	return render_template('view_quiz.html', quiz_id=quiz_id)

@app.route('/teacher/results')
def teacher_results():
	# Check if teacher is logged in
	if not session.get('teacher_logged_in'):
		flash('Please login first.', 'error')
		return redirect(url_for('teacher_login'))
	
	# Get all quizzes and their results
	quiz_results = []
	for quiz_code, quiz_data in quizzes.items():
		# Get quiz statistics
		total_attempts = 0
		total_score = 0
		scores_distribution = {
			'90-100': 0,
			'80-89': 0,
			'70-79': 0,
			'60-69': 0,
			'Below 60': 0
		}
		
		# Get results from session history
		for result in session.get('quiz_history', []):
			if result['code'] == quiz_code:
				total_attempts += 1
				total_score += result['score']
				
				# Update score distribution
				percentage = result['percentage']
				if percentage >= 90:
					scores_distribution['90-100'] += 1
				elif percentage >= 80:
					scores_distribution['80-89'] += 1
				elif percentage >= 70:
					scores_distribution['70-79'] += 1
				elif percentage >= 60:
					scores_distribution['60-69'] += 1
				else:
					scores_distribution['Below 60'] += 1
		
		# Calculate average score
		avg_score = total_score / total_attempts if total_attempts > 0 else 0
		
		quiz_results.append({
			'code': quiz_code,
			'total_attempts': total_attempts,
			'average_score': avg_score,
			'scores_distribution': scores_distribution,
			'created_at': quiz_data.get('created_at', 'N/A'),
			'question_count': len(quiz_data['questions'])
		})
	
	return render_template('teacher_results.html',
						 username=session.get('teacher_username'),
						 quiz_results=quiz_results)

if __name__ == '__main__':
	print("\nQuizGenie.AI Server is running!")
	print(f"Upload directory: {UPLOAD_FOLDER}")
	print("Access the application at: http://127.0.0.1:5001")
	print("Debug mode is ON")
	print("Press CTRL+C to quit\n")
	app.run(host='127.0.0.1', port=5001, debug=True)