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
import os
from HistoryExtraction.extract_histories import extract_histories

LOCAL_PATH = os.path.dirname(__file__)

def predict_next(ast_num, hole_pos, model, hole_sentence, index_to_word, word_to_index):
    next_word_probs = model.predict(hole_sentence)[-1]
    # print next_word_probs
    top5args = np.argsort(next_word_probs)[::-1][:5]
    top5probs = next_word_probs[top5args]
    for i in range(5):
        print(ast_num,hole_pos,i+1,top5probs[i],index_to_word[top5args[i]])


def eprint(*args, **kwargs):
    """ Help function to print to stderror stream instead stdout """
    print(*args, file=sys.stderr, **kwargs)


def bugfixForTokenizer (lst):
    ''' The tokenizer has a strange bug,
        that he does not handle the number 3 properly.'''
    correctedList = []
    for cur in lst:
        if not cur.startswith("<"):
            correctedList[-1] = correctedList[-1] + cur
        else:
            correctedList.append(cur)
    return correctedList



if __name__ == "__main__":
    astFilePath = sys.argv[1]
    testFilePath = sys.argv[2]

    try:
        # Get the histories and cut away everything after the _HOLE_
        histories = extract_histories(astFilePath, testFilePath, testOnHoles = True);
        histories = histories[0].split("\n")[:-1] #Remember also environment infos given from 1 to 4, remove empty line
        for i, history in enumerate(histories):
                histories[i] = history[:history.rfind(">", 0, history.find("_HOLE_")) + 1]



        # Load data (this may take a few minutes)
        VOCABULARY_SIZE = 3000
        X_train, y_train, word_to_index, index_to_word = load_data(LOCAL_PATH + '/fullHist.hist', VOCABULARY_SIZE)

        # Load parameters of pre-trained model
        model = load_model_parameters_theano(LOCAL_PATH + '/TrainedNetworks/pretrained.npz')

        tknzr = TweetTokenizer()

        for history in histories:
            # print sent
            word_tokens = tknzr.tokenize(history)
            word_tokens = bugfixForTokenizer(word_tokens)
            ast_num = word_tokens[0]
            hole_pos = word_tokens[1]
            hole_sentence = []

            try:
                for i in range(len(word_tokens)-2):
                    hole_sentence.append(word_to_index[word_tokens[i+2]])

                predict_next(ast_num, hole_pos, model, hole_sentence, index_to_word, word_to_index)
                print("\n")
            except Exception as e:
                eprint("History for <" + str(ast_num) + "><" + str(hole_pos) + "> too short.")

    except Exception as e:
        eprint(str(e))