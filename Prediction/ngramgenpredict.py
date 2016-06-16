import nltk
import numpy as np
import itertools
import time
import heapq

t0 = time.time()
f = open('../data/samples/Histories.txt')
raw = f.read()

from nltk.tokenize import TweetTokenizer
tknzr = TweetTokenizer()
tokens1 = tknzr.tokenize(raw)
tokens = nltk.word_tokenize(raw)

#Creation of trigrams
trigs = nltk.trigrams(tokens1)
#Creation of bigrams
bgs = nltk.bigrams(tokens1)

#Frequency distribution for all the trigrams in the text
fdisttri = nltk.FreqDist(trigs)

#Frequency distribution for all the bigrams in the text
fdistbi = nltk.FreqDist(bgs)

a, b = zip(*fdistbi.items())
key = np.arange(1,np.shape(a)[0]+1)
dict_idx = dict(zip(a,key))
frequency_list = [];
for i in range(np.shape(a)[0]):
    frequency_list.append([])
    

for k,v in fdisttri.items():
    tmp = (k[0],k[1])
    frequency_list[dict_idx[tmp]-1].append([k[2],v])

print time.time() - t0

def predict_next(searchtext, frequency_list, dict_idx):
    searchtokens = tuple(searchtext)
    elem,count = zip(*frequency_list[dict_idx[searchtokens] - 1])
    # print elem
    # print count
    res_idx = np.array(heapq.nlargest(5, range(len(count)), key=lambda x: count[x]))
    elem = np.array(elem)
    count = np.array(count)
    res = elem[res_idx]
    # print count[res_idx]
    prob = count[res_idx]/(1.*np.sum(count))
    for i in range(len(prob)):
        print i+1, res[i], prob[i]
        
with open('test.txt', 'rb') as f:
    reader = f.readlines()
    sentences = itertools.chain(*[nltk.sent_tokenize(x.decode("utf-8")) for x in reader])

for sent in sentences:
    # print sent
    word_tokens = tknzr.tokenize(sent)
    hole_sentence = []
    for i in range(2):
        hole_sentence.append(word_tokens[len(word_tokens)-2+i])
    predict_next(hole_sentence, frequency_list, dict_idx)

# total = 0
# for k,v in fdist.items():
#     if k[0]=="<rand_1,0,1,int>" and k[1]=="<rand,1,1,int>":
#         print v
#         total += v