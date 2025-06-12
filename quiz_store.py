from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random
import string
import time
import uuid

class QuizStore:
    def __init__(self):
        self.quizzes = {}
        self.submissions = {}
        self.expired_quizzes = {}
        self.expiry_time = timedelta(hours=24)  # Quizzes expire after 24 hours
        self.code_prefix = "QZ"  # Prefix for quiz codes
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # Cleanup every hour
    
    def generate_unique_code(self) -> str:
        """Generate a unique quiz code"""
        timestamp = int(time.time() * 1000)  # Get current timestamp in milliseconds
        random_part = ''.join(random.choices(string.digits + string.ascii_uppercase, k=4))
        code = f"{self.code_prefix}{random_part}{timestamp % 100:02d}"
        
        # In the unlikely event of a collision, append a random character
        while code in self.quizzes:
            code = code[:-1] + random.choice(string.ascii_uppercase)
        
        return code
    
    def create_quiz(self, questions: List[Dict], quiz_type: str, created_by: str = "teacher") -> str:
        """Create a new quiz and return its code"""
        # Periodic cleanup of expired quizzes
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self.cleanup_expired_quizzes()
            self._last_cleanup = current_time
        
        # Generate unique code
        quiz_code = str(uuid.uuid4())[:8].upper()
        
        self.quizzes[quiz_code] = {
            'questions': questions,
            'type': quiz_type,
            'created_by': created_by,
            'submissions': [],
            'created_at': datetime.now(),
            'expires_at': datetime.now() + self.expiry_time,
            'total_attempts': 0,
            'average_score': 0
        }
        
        return quiz_code
    
    def get_quiz(self, quiz_code: str) -> Optional[Dict]:
        """Get quiz by code"""
        quiz = self.quizzes.get(quiz_code)
        if quiz and datetime.now() < quiz['expires_at']:
            return quiz
        return None
    
    def get_expired_quiz(self, quiz_code: str) -> Optional[Dict]:
        """Get an expired quiz by code"""
        return self.expired_quizzes.get(quiz_code)
    
    def submit_quiz(self, quiz_code: str, student_name: str, answers: List[str]) -> Dict:
        """Submit a quiz attempt"""
        quiz = self.get_quiz(quiz_code)
        if not quiz:
            raise ValueError("Quiz not found")
        
        submission = {
            'student_name': student_name,
            'answers': answers,
            'timestamp': datetime.now()
        }
        
        if quiz_code not in self.submissions:
            self.submissions[quiz_code] = []
        
        self.submissions[quiz_code].append(submission)
        quiz['submissions'].append(submission)
        
        # Calculate score
        questions = quiz['questions']
        if len(answers) != len(questions):
            raise ValueError("Number of answers does not match number of questions")
        
        # Optimize score calculation
        correct_count = sum(
            1 for q, a in zip(questions, answers)
            if a.lower() == q['correct_answer'].lower()
        )
        
        # Calculate percentage score
        score_percentage = (correct_count / len(questions)) * 100
        
        # Create response object with feedback
        feedback = [
            {
                'question_num': i + 1,
                'correct': a.lower() == q['correct_answer'].lower(),
                'student_answer': a,
                'correct_answer': q['correct_answer']
            }
            for i, (q, a) in enumerate(zip(questions, answers))
        ]
        
        # Create response object
        response = {
            'student_name': student_name,
            'submission_time': submission['timestamp'],
            'score': correct_count,
            'score_percentage': score_percentage,
            'total_questions': len(questions),
            'answers': answers,
            'feedback': feedback
        }
        
        # Update quiz statistics efficiently
        quiz['total_attempts'] += 1
        quiz['average_score'] = (
            (quiz['average_score'] * (quiz['total_attempts'] - 1) + score_percentage)
            / quiz['total_attempts']
        )
        
        return response
    
    def get_quiz_responses(self, quiz_code: str) -> List[Dict]:
        """Get all responses for a quiz"""
        return self.submissions.get(quiz_code, [])
    
    def get_quiz_stats(self, quiz_code: str) -> Optional[Dict]:
        """Get statistics for a quiz"""
        quiz = self.get_quiz(quiz_code)
        if not quiz:
            return None
        
        submissions = self.submissions.get(quiz_code, [])
        total_submissions = len(submissions)
        
        if total_submissions == 0:
            return {
                'total_attempts': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0,
                'submissions': []
            }
        
        # Calculate scores for each submission
        detailed_submissions = []
        scores = []
        
        for submission in submissions:
            correct_answers = 0
            for q_idx, (question, answer) in enumerate(zip(quiz['questions'], submission['answers'])):
                if answer.lower() == question['correct_answer'].lower():
                    correct_answers += 1
            
            score_percentage = (correct_answers / len(quiz['questions'])) * 100
            scores.append(score_percentage)
            
            detailed_submissions.append({
                'student_name': submission['student_name'],
                'score': correct_answers,
                'total': len(quiz['questions']),
                'percentage': round(score_percentage, 1),
                'timestamp': submission['timestamp']
            })
        
        return {
            'total_attempts': total_submissions,
            'average_score': round(sum(scores) / len(scores), 1),
            'highest_score': round(max(scores), 1) if scores else 0,
            'lowest_score': round(min(scores), 1) if scores else 0,
            'submissions': detailed_submissions
        }
    
    def cleanup_expired_quizzes(self):
        """Remove expired quizzes and their responses"""
        current_time = datetime.now()
        expired_codes = [
            code for code, quiz in self.quizzes.items()
            if current_time >= quiz['expires_at']
        ]
        
        for code in expired_codes:
            self.quizzes.pop(code, None)
            self.submissions.pop(code, None)
            self.expired_quizzes[code] = self.quizzes.get(code)
        
        self._last_cleanup = time.time() 