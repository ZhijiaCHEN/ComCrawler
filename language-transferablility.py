import csv, os, pickle
from collections import defaultdict
from fasttext_classification import comment_preprocess

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.metrics import precision_recall_fscore_support
from datetime import datetime

from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier

import numpy as np

vectorizer = TfidfVectorizer(max_features=1000)
path = 'D:\\Google Drive\\Temple\\projects\\comment entry\\data\\button'

wid2lan = {}
lanCnt = defaultdict(int)
with open(os.path.join(path, 'wid2language.csv'), encoding='utf-8') as f:
    x = csv.reader(f, delimiter=' ')
    for r in x:
        wid2lan[int(r[0])] = r[1]
        lanCnt[r[1]] += 1

if '中文' in lanCnt:
    lanCnt['中文'] = 8

topLan = [x[0] for x in sorted(lanCnt.items(), key=lambda x:x[1], reverse=True)]
topLan = ['zh-cn', 'en', 'es', 'de', 'fr']
recall, precision = {}, {}
for lan in topLan[:5]:
    XTrain, YTrain, XTest, YTest = [], [], [], []
    for fileName in os.listdir(os.path.join(path, 'preprocessed')):
        filePath = os.path.join(path, 'preprocessed', fileName)
        f = fileName.split('-')
        y = 1 if f[0] == 'positive' else 0
        wid = int(f[1])
        with open(filePath, encoding='utf-8') as file:
            x = file.read()
            if wid2lan[wid] == lan:
                XTest.append(x)
                YTest.append(y)
            else:
                XTrain.append(x)
                YTrain.append(y)
    XTrain = vectorizer.fit_transform(XTrain)
    XTest = vectorizer.transform(XTest)
    YTrain = np.array(YTrain)
    YTest = np.array(YTest)
    clf = RandomForestClassifier()
    clf.fit(XTrain, YTrain)
    s = precision_recall_fscore_support(YTest, clf.predict(XTest), average='binary')
    print(f'Score on {lan}: {s}')



