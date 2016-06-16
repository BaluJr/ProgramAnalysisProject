import numpy as np
import itertools
from nltk.tokenize import TweetTokenizer
import nltk
import theano as theano
import theano.tensor as T
import time
import operator
from utils import *
from gru_theano import *
import sys

def predict_next(model, hole_sentence, index_to_word, word_to_index):
    next_word_probs = model.predict(hole_sentence)[-1]
    # print next_word_probs
    top5args = np.argsort(next_word_probs)[::-1][:5]
    top5probs = next_word_probs[top5args]
    for i in range(5):
        print i+1,top5probs[i],index_to_word[top5args[i]]
    

# Load data (this may take a few minutes)
VOCABULARY_SIZE = 3000
X_train, y_train, word_to_index, index_to_word = load_data("../data/samples/Histories.txt", VOCABULARY_SIZE)

# Load parameters of pre-trained model
model = load_model_parameters_theano('pretrained.npz')

tknzr = TweetTokenizer()
# Read the data and append SENTENCE_START and SENTENCE_END tokens
with open('test.txt', 'rb') as f:
    reader = f.readlines()
    sentences = itertools.chain(*[nltk.sent_tokenize(x.decode("utf-8")) for x in reader])

for sent in sentences:
    # print sent
    word_tokens = tknzr.tokenize(sent)
    hole_sentence = []
    for i in range(len(word_tokens)):
        hole_sentence.append(word_to_index[word_tokens[i]])
    predict_next(model, hole_sentence, index_to_word, word_to_index)
    # print hole_sentence


