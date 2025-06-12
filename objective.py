# objective.py

import re
import nltk
import numpy as np
from nltk.corpus import wordnet as wn
from nltk.tokenize import word_tokenize, sent_tokenize
from transformers import pipeline
from nltk.corpus import stopwords
import random

class ObjectiveTest:
    def __init__(self, text, num_questions):
        self.text = text
        self.num_questions = num_questions
        self.generator = pipeline("text2text-generation", model="google/flan-t5-base")
        self.qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")

    def preprocess_text(self):
        """Preprocess the text to get meaningful sentences"""
        sentences = sent_tokenize(self.text)
        # Filter out short sentences and those without important content
        stop_words = set(stopwords.words('english'))
        meaningful_sentences = []
        
        for sent in sentences:
            words = word_tokenize(sent.lower())
            words = [w for w in words if w.isalnum()]
            if len(words) > 8:  # Minimum sentence length
                content_words = [w for w in words if w not in stop_words]
                if len(content_words) > 5:  # Minimum content words
                    meaningful_sentences.append(sent)
                    
        return meaningful_sentences

    def generate_distractors(self, answer, context):
        """Generate plausible distractors for multiple choice"""
        try:
            # Use similar words from context
            words = word_tokenize(context.lower())
            words = [w for w in words if w.isalnum() and w not in stopwords.words('english')]
            
            # Get unique words that are different from the answer
            distractors = list(set([w.capitalize() for w in words 
                                  if w not in answer.lower() 
                                  and len(w) > 3]))
            
            # Select random distractors
            if len(distractors) >= 3:
                return random.sample(distractors, 3)
            else:
                # If not enough distractors, generate some basic ones
                return [f"Not {answer}", f"None of the above", f"All of the above"]
        except Exception:
            return [f"Not {answer}", f"None of the above", f"All of the above"]

    def generate_test(self):
        """Generate multiple choice questions"""
        try:
            meaningful_sentences = self.preprocess_text()
            if len(meaningful_sentences) < self.num_questions:
                raise ValueError("Not enough content to generate requested number of questions")

            # Select random sentences for question generation
            selected_sentences = random.sample(meaningful_sentences, self.num_questions)
            
            questions = []
            answers = []
            
            for context in selected_sentences:
                # Generate question using text2text model
                prompt = f"Generate a factual question about this text: {context}"
                question = self.generator(prompt, max_length=50, num_return_sequences=1)[0]['generated_text']
                
                # Get answer using question-answering model
                qa_result = self.qa_pipeline(question=question, context=context)
                correct_answer = qa_result['answer']
                
                # Generate distractors
                distractors = self.generate_distractors(correct_answer, context)
                
                # Create multiple choice options
                options = [correct_answer] + distractors
                random.shuffle(options)
                
                # Find the correct option letter
                correct_option = chr(65 + options.index(correct_answer))  # A, B, C, or D
                
                # Format the question with options
                formatted_question = f"{question}\n"
                for i, opt in enumerate(options):
                    formatted_question += f"{chr(65 + i)}) {opt}\n"
                
                questions.append(formatted_question.strip())
                answers.append(correct_option)
            
            return questions, answers
            
        except Exception as e:
            raise Exception(f"Error generating questions: {str(e)}")

    def get_trivial_sentences(self):
        sentences = sent_tokenize(self.text)
        trivial_sentences = []
        for sent in sentences:
            trivial = self.identify_trivial_sentences(sent)
            if trivial:
                trivial_sentences.append(trivial)
        return trivial_sentences

    def identify_trivial_sentences(self, sentence):
        tokens = word_tokenize(sentence)
        if len(tokens) < 4:
            return None
        tags = nltk.pos_tag(tokens)
        if tags[0][1] == "RB":
            return None

        grammar = r"""
            CHUNK: {<NN>+<IN|DT>*<NN>+}
                   {<NN>+<IN|DT>*<NNP>+}
                   {<NNP>+<NNS>*}
        """
        chunker = nltk.RegexpParser(grammar)
        tree = chunker.parse(tags)

        noun_phrases = []
        for subtree in tree.subtrees():
            if subtree.label() == "CHUNK":
                phrase = " ".join(word for word, tag in subtree)
                noun_phrases.append(phrase)

        replace_nouns = []
        for word, _ in tags:
            for phrase in noun_phrases:
                if phrase[0] == '\'':
                    break
                if word in phrase:
                    replace_nouns.extend(phrase.split()[-2:])
                    break
            if not replace_nouns:
                replace_nouns.append(word)
            break

        if not replace_nouns:
            return None

        trivial = {
            "Answer": " ".join(replace_nouns),
            "Similar": self.answer_options(replace_nouns[0]) if len(replace_nouns) == 1 else []
        }

        replace_phrase = " ".join(replace_nouns)
        sentence_with_blank = re.sub(re.escape(replace_phrase), "__________", sentence, flags=re.IGNORECASE, count=1)
        trivial["Question"] = sentence_with_blank.strip()
        return trivial

    @staticmethod
    def answer_options(word):
        synsets = wn.synsets(word, pos="n")
        if not synsets:
            return []
        hypernyms = synsets[0].hypernyms()
        if not hypernyms:
            return []
        hyponyms = hypernyms[0].hyponyms()
        similar_words = []
        for hyponym in hyponyms:
            similar_word = hyponym.lemmas()[0].name().replace("_", " ")
            if similar_word.lower() != word.lower():
                similar_words.append(similar_word)
            if len(similar_words) >= 8:
                break
        return similar_words
