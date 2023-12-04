import csv, os, pickle
from collections import defaultdict
from fasttext_classification import comment_preprocess

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.metrics import precision_recall_fscore_support
from datetime import datetime

from sklearn.svm import SVC
from sklearn.model_selection import GroupKFold
from sklearn.utils import shuffle 
import numpy as np
from statistics import mean, stdev


path = r'D:\Google Drive\Temple\projects\comment entry\data\comment\preprocessed'

def classification_k_group(path, k = 10):
    File = [f for f in os.listdir(path) if f.split('.')[1] == 'txt']
    X = [open(os.path.join(path, f), encoding='utf-8').read() for f in File]
    X = np.array(X)
    Y = np.array([1 if x[0] == 'p' else 0 for x in File])
    G = np.array([int(f.split('-')[1]) for f in File])
    X, Y, G = shuffle(X, Y, G)
    gKFold = GroupKFold(n_splits=k)

    for s in range(10, 101, 10):
        vectorizer = TfidfVectorizer(max_features=s)
        recallL = []
        precisionL = []
        fscoreL = []
        cnt = 0
        for trainIndex, testIndex in gKFold.split(X, Y, G):
            cnt += 1
            print(f"Running for size = {s}, cnt = {cnt}.")
            XTrain = vectorizer.fit_transform(X[trainIndex])
            YTrain = Y[trainIndex]
            XTest = vectorizer.transform(X[testIndex])
            YTest = Y[testIndex]
            clf = SVC(kernel='poly', degree=3)
            clf.fit(XTrain, YTrain)
            score = precision_recall_fscore_support(YTest, clf.predict(XTest), labels=[1])
            precisionL.append(score[0][0])
            recallL.append(score[1][0])
            fscoreL.append(score[2][0])
            print(f"TF-IDF size = {s}, cnt = {cnt}, score = {score}.")
        print(f"TF-IDF vector size {s} {k}-fold cross validation: precision={mean(precisionL)}({stdev(precisionL)}), recall={mean(recallL)}({stdev(recallL)}), F1={mean(fscoreL)}({stdev(fscoreL)})")

classification_k_group(path)


