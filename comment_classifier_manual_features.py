import dateparser, string
import os, re
from lxml import etree
from nltk.corpus import stopwords
from nltk.corpus.reader.chasen import test
from nltk.tokenize import word_tokenize
import numpy as np
from numpy import testing
from comment_classifier_datetime import build_signature_dict
from sklearn.model_selection import GroupKFold
from sklearn.svm import SVC
from sklearn.metrics import precision_recall_fscore_support

parser = etree.HTMLParser(encoding='utf-8', remove_comments=True)
pPath = r'D:\Google Drive\Temple\projects\comment entry\data\comment\positive'
nPath = r'D:\Google Drive\Temple\projects\comment entry\data\comment\negative'
outputPath = r'D:\Google Drive\Temple\projects\comment entry\data\comment\mannual-features'

def feature_extraction(file):
    tree = etree.parse(file, parser=parser)
    numberOfAnchors = len(tree.xpath('//a'))
    blockWithTag = etree.tostring(tree).lower()
    blockWithoutTag = re.sub('\s+', ' ', tree.xpath('string(//*)')).lower()
    blockLengthWithTag = len(blockWithTag)
    blockLengthWithoutTag = len(blockWithoutTag)
    numberOfWords = len(blockWithoutTag.split(' '))
    numberOfComment = blockWithoutTag.count('comment')
    anchorRatio = numberOfAnchors / blockLengthWithTag
    stopWordsSet = set(stopwords.words())
    wordTokens = word_tokenize(blockWithoutTag)
    stopWords = [x for x in wordTokens if x in stopWordsSet]
    numberOfStopWords = len(stopWords)
    stopWordsRatio = numberOfStopWords / blockLengthWithTag
    punctuation = [x for x in blockWithoutTag if x in string.punctuation]
    numberOfPunctuation = len(punctuation)
    punctuationRatio = len(punctuation) / blockLengthWithTag

    numberOfDateTime = 0
    strSignatureDict = build_signature_dict(file)
    for signature, candidate in strSignatureDict.items():
        if len(candidate) < 5 or len([x for y in signature for x in y]) <= 1:
                continue
        datetimeS = [y for y in [dateparser.parse(x) for x in candidate] if y is not None]
        # ret = max(ret, len(datetimeS))
        numberOfDateTime += len(datetimeS)
    datatimeRatio = numberOfDateTime / blockLengthWithTag

    ret = [blockLengthWithoutTag, blockLengthWithTag, numberOfWords, numberOfComment, anchorRatio, numberOfAnchors, stopWordsRatio, numberOfStopWords, punctuationRatio, numberOfPunctuation, numberOfDateTime, datatimeRatio]
    return ret

def generate_feature():
    X = []
    cnt = 0
    for f in os.listdir(pPath):
        if f.split('.')[-1] != 'html':
            continue
        file = os.path.join(pPath, f)
        print(f"Processing {file}.")
        x = f"1,{f.split('.')[0].split('-')[0]}," + ','.join([str(x) for x in feature_extraction(file)]) + '\n'
        X.append(x)
        cnt += 1
        # if cnt >= 3:
        #     break

    for f in os.listdir(nPath):
        if f.split('.')[-1] != 'html':
            continue
        file = os.path.join(nPath, f)
        print(f"Processing {file}.")
        x = f"1,{f.split('.')[0].split('-')[0]}," + ','.join([str(x) for x in feature_extraction(file)]) + '\n'
        X.append(x)
        cnt += 1
        # if cnt >= 6:
        #     break

    with open(os.path.join(outputPath, 'features.txt'), 'w') as f:
        f.writelines(X)

if __name__ == '__main__':
    with open(os.path.join(outputPath, 'features.txt')) as f:
        X = [x.split(',') for x in f.readlines()]
        y = [0] * len(X)
        y[:1981] = [1] * 1981
        y = np.array(y)
        G = [int(x[1]) for x in X]
        X = np.array([[float(y) for y in x[2:]] for x in X])
        gKFold = GroupKFold(n_splits=10)
        clf = SVC(kernel='rbf', gamma='scale')
        recallL = []
        precisionL = []
        fscoreL = []
        for trainIndex, testIndex in gKFold.split(X, y, G):
            clf.fit(X[trainIndex], y[trainIndex])
            yPred = clf.predict(X[testIndex])
            score = precision_recall_fscore_support(y[testIndex], yPred, labels=[1])
            precisionL.append(score[0][0])
            recallL.append(score[1][0])
            fscoreL.append(score[2][0])
            # print(precisionL[-1], recallL[-1], fscoreL[-1])
        recallL = np.array(recallL)
        precisionL = np.array(precisionL)
        fscoreL = np.array(fscoreL)
        print(f"Precision: {np.average(precisionL)}({np.std(precisionL)}), recall: {np.average(recallL)}({np.std(recallL)}), Fscore: {np.average(fscoreL)}({np.std(fscoreL)})")



