# bert_model.py

from transformers import BertTokenizer, BertForSequenceClassification
import torch

# Load pre-trained model and tokenizer
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=2)

def predict_question_type(question):
    inputs = tokenizer(question, return_tensors="pt", truncation=True, padding=True, max_length=512)
    outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=1)
    prediction = torch.argmax(probs).item()
    
    if prediction == 0:
        return "objective"
    else:
        return "subjective"
