from __future__ import print_function
import nltk
import numpy as np
import itertools
import time
import heapq
import sys
from HistoryExtraction.extract_histories import extract_histories
import os
from nltk.tokenize import TweetTokenizer
import pickle

LOCAL_PATH = os.path.dirname(__file__)

def predict_next(ast_num, hole_pos, searchtext, frequency_list, dict_idx):
    searchtokens = tuple(searchtext)
    elem,count = zip(*frequency_list[dict_idx[searchtokens] - 1])
    res_idx = np.array(heapq.nlargest(5, range(len(count)), key=lambda x: count[x]))
    elem = np.array(elem)
    count = np.array(count)
    res = elem[res_idx]
    # print count[res_idx]
    prob = count[res_idx]/(1.*np.sum(count))
    for i in range(len(prob)):
        print(ast_num, hole_pos, i+1, res[i], prob[i])


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


def eprint(*args, **kwargs):
    """ Help function to print to stderror stream instead stdout """
    print(*args, file=sys.stderr, **kwargs)


if __name__ == "__main__":
    astFilePath = sys.argv[1]
    testFilePath = sys.argv[2]

    try:
        # Get the histories and cut away everything after the _HOLE_
        histories = extract_histories(astFilePath, testFilePath, testOnHoles = True);
        histories = histories[0].split("\n")[:-1] #Remember also environment infos given from 1 to 4, remove empty line
        for i, history in enumerate(histories):
            histories[i] = history[:history.rfind(">", 0, history.find("_HOLE_")) + 1]

        t0 = time.time()

        # Currently the VM is quiete slow when accessing the HDD. It is not sure, whether it is faster to prozcess
        # tokens again or to deserialize the pickle file.
        # When model already available load it
        # if os.path.isfile(LOCAL_PATH + '/TrainedNetworks/ngramTokens.pkl') and os.path.isfile(LOCAL_PATH + '/TrainedNetworks/ngramTokens1.pkl'):
        #    print ("Available")
        #    pkl_file = open(LOCAL_PATH + '/TrainedNetworks/ngramTokens.pkl', 'rb')
        #    tokens = pickle.load(pkl_file)
        #    pkl_file.close()
        #    pkl_file = open(LOCAL_PATH + '/TrainedNetworks/ngramTokens1.pkl', 'rb')
        #    tokens1 = pickle.load(pkl_file)
        #    pkl_file.close()
        #
        # # When model not yet available calculate and store it
        # else:
        #
        #     f = open(LOCAL_PATH + '/fullHist.hist')
        #     raw = f.read()
        #     tknzr = TweetTokenizer()
        #     tokens1 = tknzr.tokenize(raw)
        #     #tokens1 = bugfixForTokenizer(tokens1)
        #     tokens = nltk.word_tokenize(raw)
        #     #tokens = bugfixForTokenizer(tokens)
        #
        #     output = open( LOCAL_PATH + '/TrainedNetworks/ngramTokens.pkl', 'w+')
        #     pickle.dump(tokens, output, -1)
        #     output.close()
        #     output = open(LOCAL_PATH + '/TrainedNetworks/ngramTokens1.pkl', 'w+')
        #     pickle.dump(tokens1, output, -1)
        #     output.close()

        f = open(LOCAL_PATH + '/fullHist.hist')
        raw = f.read()
        tknzr = TweetTokenizer()
        tokens1 = tknzr.tokenize(raw)
        #tokens1 = bugfixForTokenizer(tokens1)
        tokens = nltk.word_tokenize(raw)
        #tokens = bugfixForTokenizer(tokens)

        # Creation of trigrams
        trigs = nltk.trigrams(tokens1)
        # Creation of bigrams
        bgs = nltk.bigrams(tokens1)

        # Frequency distribution for all the trigrams in the text
        fdisttri = nltk.FreqDist(trigs)

        # Frequency distribution for all the bigrams in the text
        fdistbi = nltk.FreqDist(bgs)

        a, b = zip(*fdistbi.items())
        key = np.arange(1, np.shape(a)[0] + 1)
        dict_idx = dict(zip(a, key))
        frequency_list = [];
        for i in range(np.shape(a)[0]):
            frequency_list.append([])

        for k, v in fdisttri.items():
            tmp = (k[0], k[1])
            frequency_list[dict_idx[tmp] - 1].append([k[2], v])

        print(time.time() - t0)


        for history in histories:
            # print sent
            word_tokens = tknzr.tokenize(history)
            word_tokens = bugfixForTokenizer(word_tokens)
            hole_sentence = []
            ast_num = word_tokens[0]
            hole_pos = word_tokens[1]
            try:
                for i in range(2):
                    hole_sentence.append(word_tokens[len(word_tokens)-2+i])
                predict_next(ast_num, hole_pos, hole_sentence, frequency_list, dict_idx)
                print("\n")
            except Exception as e:
                eprint("History for <" + str(ast_num) + "><" + str(hole_pos) + "> too short.")


    except Exception as e:
        eprint(str(e))