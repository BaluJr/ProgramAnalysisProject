from __future__ import print_function
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


def eprint(*args, **kwargs):
    """ Help function to print to stderror stream instead stdout """
    print(*args, file=sys.stderr, **kwargs)


if __name__ == "__main__":
    astFilePath = sys.argv[1]
    testFilePath = sys.argv[2]

    try:
        # Get the histories and cut away everything after the _HOLE_
        histories = extract_histories(astFilePath, testFilePath, testOnHoles = True);
        histories = histories[0].split("\n") #Remember also environment infos given from 1 to 4
        for i, history in enumerate(histories):
            histories[i] = history[:history.rfind(">", 0, history.find("_HOLE_")) + 1]



        # Load data (this may take a few minutes)
        VOCABULARY_SIZE = 3000
        X_train, y_train, word_to_index, index_to_word = load_data(astFilePath, VOCABULARY_SIZE)

        # Load parameters of pre-trained model
        #model = load_model_parameters_theano('TrainedNetworks/pretrained.npz')

        tknzr = TweetTokenizer()
        # Read the data and append SENTENCE_START and SENTENCE_END tokens
        with open(testFilePath, 'rb') as f:
            reader = f.readlines()
            sentences = itertools.chain(*[nltk.sent_tokenize(x.decode("utf-8")) for x in reader])


        # Get the positions for printout
        positions = []
        with open(testFilePath, 'rb'):
            for line in testFilePath:
                positions.append(line.split(" "))


        for sent in sentences:
            # print sent
            word_tokens = tknzr.tokenize(sent)
            hole_sentence = []
            for i in range(len(word_tokens)):
                hole_sentence.append(word_to_index[word_tokens[i]])
            predict_next(model, hole_sentence, index_to_word, word_to_index)
            # print hole_sentence

    except Exception as e:
        eprint(str(e))
