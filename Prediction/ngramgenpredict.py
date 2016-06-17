from __future__ import print_function
import nltk
import numpy as np
import itertools
import time
import heapq
import sys
from HistoryExtraction.extract_histories import extract_histories

from nltk.tokenize import TweetTokenizer

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

        t0 = time.time()
        f = open('fullHist.hist')
        raw = f.read()

        tknzr = TweetTokenizer()
        tokens1 = tknzr.tokenize(raw)
        tokens = nltk.word_tokenize(raw)

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
            hole_sentence = []
            ast_num = word_tokens[0]
            hole_pos = word_tokens[1]
            for i in range(2):
                hole_sentence.append(word_tokens[len(word_tokens)-2+i])
            predict_next(ast_num, hole_pos, hole_sentence, frequency_list, dict_idx)


    except Exception as e:
        eprint(str(e))