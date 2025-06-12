import nltk
import random
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
import logging
import PyPDF2
import docx
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ' '.join(page.extract_text() for page in reader.pages)
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file_path)
        text = ' '.join(paragraph.text for paragraph in doc.paragraphs)
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        raise

def extract_text(file_path):
    """Extract text from supported file types"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_extension in ['.docx', '.doc']:
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

def generate_quiz(file_path, num_questions=10, quiz_type='mcq'):
    """Generate quiz questions from document"""
    try:
        # Extract text from document
        text = extract_text(file_path)
        
        # Generate questions based on type
        if quiz_type == 'mcq':
            questions = []
            sentences = sent_tokenize(text)
            used_answers = set()  # Track used answers
            
            # Process only as many sentences as needed
            for sentence in sentences[:num_questions * 2]:  # Process more sentences than needed to ensure enough good ones
                words = word_tokenize(sentence)
                tagged = pos_tag(words)
                
                # Find important words that haven't been used as answers
                important_words = [(word, tag) for word, tag in tagged 
                                 if tag.startswith(('NN', 'VB', 'JJ')) 
                                 and word.lower() not in stopwords.words('english')
                                 and word.lower() not in used_answers
                                 and len(word) > 3]
                
                if important_words:
                    word_to_replace, tag = random.choice(important_words)
                    if word_to_replace.lower() not in used_answers:  # Double check
                        question_text = f"What is the correct word in: '{sentence.replace(word_to_replace, '_____')}'"
                        
                        # Generate exactly 4 options
                        options = [word_to_replace]  # Correct answer is always first
                        
                        # Add similar words from sentence
                        similar_words = [w for w, t in tagged if t == tag and w != word_to_replace]
                        if similar_words:
                            options.extend(random.sample(similar_words, min(2, len(similar_words))))
                        
                        # Add generic options until we have exactly 4
                        generic_options = {
                            'NN': ['object', 'item', 'thing', 'element', 'part', 'system', 'component'],
                            'VB': ['make', 'take', 'give', 'find', 'show', 'create', 'perform'],
                            'JJ': ['good', 'new', 'first', 'last', 'long', 'important', 'different']
                        }
                        
                        tag_prefix = tag[:2]  # Get NN, VB, or JJ
                        while len(options) < 4:
                            generic = random.choice(generic_options.get(tag_prefix, generic_options['NN']))
                            if generic not in options:
                                options.append(generic)
                        
                        # Ensure exactly 4 unique options
                        options = list(dict.fromkeys(options))[:4]
                        while len(options) < 4:  # In case we still don't have 4 unique options
                            generic = random.choice(generic_options.get(tag_prefix, generic_options['NN']))
                            if generic not in options:
                                options.append(generic)
                        
                        # Remember the correct answer
                        correct_answer = word_to_replace
                        used_answers.add(word_to_replace.lower())
                        
                        # Shuffle options
                        random.shuffle(options)
                        
                        # Find the new index of the correct answer
                        correct_index = options.index(correct_answer)
                        
                        questions.append({
                            'question': question_text,
                            'options': options,
                            'correct': correct_index,
                            'type': 'mcq'
                        })
                        
                        if len(questions) >= num_questions:
                            break
            
            return questions
            
        elif quiz_type == 'true_false':
            questions = []
            sentences = sent_tokenize(text)[:num_questions]
            
            for sentence in sentences:
                correct = random.choice([True, False])
                if not correct:
                    # Simple modification for false statements
                    words = sentence.split()
                    if len(words) > 3:
                        pos = random.randint(0, len(words)-1)
                        words[pos] = random.choice(['not', 'never', 'rarely', 'hardly'])
                        sentence = ' '.join(words)
                
                questions.append({
                    'question': sentence,
                    'type': 'true_false',
                    'correct': 0 if correct else 1
                })
            
            return questions
            
        elif quiz_type == 'fill_blanks':
            return generate_fill_blanks(text, num_questions)
            
        else:
            raise ValueError(f"Unsupported quiz type: {quiz_type}")
            
    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        raise

def clean_text(text):
    """Clean and preprocess text"""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove special characters but keep punctuation
    text = ''.join(char for char in text if char.isalnum() or char.isspace() or char in '.,!?')
    return text

def generate_mcq_questions(text, num_questions):
    """Generate multiple choice questions with optimized processing"""
    try:
        # Tokenize text into sentences
        sentences = sent_tokenize(text)
        
        # Process sentences in parallel
        with ThreadPoolExecutor() as executor:
            # Process sentences in chunks for better performance
            chunk_size = min(10, len(sentences))
            sentence_chunks = [sentences[i:i + chunk_size] for i in range(0, len(sentences), chunk_size)]
            
            questions = []
            used_words = set()
            
            for chunk in sentence_chunks:
                if len(questions) >= num_questions:
                    break
                    
                # Process chunk of sentences in parallel
                futures = []
                for sentence in chunk:
                    futures.append(executor.submit(process_sentence, sentence, used_words))
                
                # Collect results
                for future in as_completed(futures):
                    result = future.result()
                    if result and len(questions) < num_questions:
                        questions.append(result)
                        if result.get('correct_answer'):
                            used_words.add(result['correct_answer'].lower())
            
            return questions[:num_questions]
            
    except Exception as e:
        logger.error(f"Error generating MCQ questions: {str(e)}")
        raise

def process_sentence(sentence, used_words):
    """Process a single sentence to generate a question"""
    words = word_tokenize(sentence)
    tagged = pos_tag(words)
    
    # Find important words that haven't been used
    important_words = [(word, tag) for word, tag in tagged 
                      if tag.startswith(('NN', 'VB', 'JJ')) 
                      and word.lower() not in stopwords.words('english')
                      and word.lower() not in used_words
                      and len(word) > 3]
    
    if important_words:
        word_to_replace, tag = random.choice(important_words)
        
        # Generate question
        question_text = f"What is the correct word in: '{sentence.replace(word_to_replace, '_____')}'"
        
        # Generate options quickly
        options = [word_to_replace]  # Correct answer
        
        # Add similar words from the sentence first
        similar_words = [w for w, t in tagged if t == tag and w != word_to_replace]
        if similar_words:
            options.extend(random.sample(similar_words, min(2, len(similar_words))))
        
        # If we need more options, add them based on word type
        while len(options) < 4:
            if tag.startswith('NN'):
                options.append(random.choice(['object', 'item', 'thing', 'element', 'part']))
            elif tag.startswith('VB'):
                options.append(random.choice(['make', 'take', 'give', 'find', 'show']))
            elif tag.startswith('JJ'):
                options.append(random.choice(['good', 'new', 'first', 'last', 'long']))
            
            # Remove duplicates
            options = list(dict.fromkeys(options))
        
        # Shuffle options
        random.shuffle(options)
        
        return {
            'question': question_text,
            'options': options[:4],  # Ensure exactly 4 options
            'correct': options.index(word_to_replace),
            'correct_answer': word_to_replace,
            'type': 'mcq'
        }
    
    return None

def generate_true_false_questions(text, num_questions):
    """Generate true/false questions"""
    sentences = sent_tokenize(text)
    questions = []
    
    for sentence in sentences[:num_questions]:
        words = word_tokenize(sentence)
        tagged = pos_tag(words)
        
        # Create a false statement by modifying the sentence
        modified = sentence
        correct_answer = random.choice([True, False])
        
        if not correct_answer:
            # Modify sentence to make it false
            for i, (word, tag) in enumerate(tagged):
                if tag.startswith(('JJ', 'RB', 'VB')):
                    antonyms = {
                        'good': 'bad', 'bad': 'good',
                        'high': 'low', 'low': 'high',
                        'large': 'small', 'small': 'large',
                        'fast': 'slow', 'slow': 'fast',
                        'early': 'late', 'late': 'early',
                        'hot': 'cold', 'cold': 'hot',
                        'new': 'old', 'old': 'new',
                        'right': 'wrong', 'wrong': 'right'
                    }
                    if word.lower() in antonyms:
                        modified = modified.replace(word, antonyms[word.lower()])
                        break
        
        questions.append({
            'question': modified,
            'type': 'true_false',
            'correct': 0 if correct_answer else 1
        })
        
        if len(questions) >= num_questions:
            break
    
    return questions

def generate_fill_blanks(text, num_questions):
    """Generate fill in the blanks questions"""
    questions = []
    sentences = sent_tokenize(text)
    used_answers = set()  # Track used answers to avoid duplicates
    
    for sentence in sentences:
        if len(questions) >= num_questions:
            break
            
        words = word_tokenize(sentence)
        tagged = pos_tag(words)
        
        # Find important nouns or key terms
        important_words = [(word, i) for i, (word, tag) in enumerate(tagged) 
                         if (tag.startswith('NN') or tag.startswith('JJ') or tag.startswith('VB'))
                         and len(word) > 3
                         and word.lower() not in stopwords.words('english')
                         and word.lower() not in used_answers]  # Check if answer was already used
        
        if important_words:
            word, _ = random.choice(important_words)
            # Only add if the answer is unique
            if word.lower() not in used_answers:
                blank_sentence = sentence.replace(word, '_____', 1)
                questions.append({
                    'question': blank_sentence,
                    'type': 'fill_blanks',
                    'options': [word],
                    'correct': 0
                })
                used_answers.add(word.lower())  # Add to used answers
    
    return questions 