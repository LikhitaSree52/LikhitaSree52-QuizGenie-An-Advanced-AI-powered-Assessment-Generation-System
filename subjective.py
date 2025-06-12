from transformers import pipeline
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import random

class SubjectiveTest:
    def __init__(self, text, num_questions):
        self.text = text
        self.num_questions = num_questions
        self.generator = pipeline("text2text-generation", model="google/flan-t5-base")
        
    def preprocess_text(self):
        """Preprocess the text to get meaningful paragraphs"""
        # Split text into sentences
        sentences = sent_tokenize(self.text)
        
        # Group sentences into paragraphs (3-4 sentences each)
        paragraphs = []
        current_para = []
        
        for sent in sentences:
            current_para.append(sent)
            if len(current_para) >= 3:
                paragraphs.append(' '.join(current_para))
                current_para = []
        
        if current_para:  # Add remaining sentences
            paragraphs.append(' '.join(current_para))
            
        return paragraphs

    def generate_question_types(self):
        """Generate different types of question starters"""
        return [
            "Explain how",
            "Describe why",
            "Analyze the",
            "Compare and contrast",
            "What are the implications of",
            "Evaluate the importance of",
            "Discuss the relationship between",
            "What conclusions can be drawn about",
            "How would you interpret",
            "What evidence supports"
        ]

    def generate_test(self):
        """Generate subjective questions with sample answers"""
        try:
            paragraphs = self.preprocess_text()
            if len(paragraphs) < self.num_questions:
                raise ValueError("Not enough content to generate requested number of questions")

            # Select random paragraphs for question generation
            selected_paragraphs = random.sample(paragraphs, self.num_questions)
            question_types = self.generate_question_types()
            
            questions = []
            answers = []
            
            for context in selected_paragraphs:
                # Generate question using text2text model
                prompt = f"Generate a thought-provoking question about this text: {context}"
                question = self.generator(prompt, max_length=50, num_return_sequences=1)[0]['generated_text']
                
                # Transform into an analytical/subjective question
                question_type = random.choice(question_types)
                transformed_question = f"{question_type} {question.lower()}"
                
                # Use the context as a sample answer
                sample_answer = f"Sample Answer: {context}"
                
                questions.append(transformed_question)
                answers.append(sample_answer)
                
                if len(questions) >= self.num_questions:
                    break
            
            return questions, answers
            
        except Exception as e:
            raise Exception(f"Error generating subjective questions: {str(e)}")
