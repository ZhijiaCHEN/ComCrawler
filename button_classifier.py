from lxml import etree
from nltk.util import ngrams

from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.base import BaseEstimator, TransformerMixin
from utility import ObjXPATH
import psycopg2, re, os, random, numpy as np, pandas as pd, pickle
from utility import custom_attrib, extract_text, extract_attributes
from ast import literal_eval
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime
parser = etree.HTMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True, default_doctype=False)
# dbConn = None
# dbCursor = None
# try:
#     dbConn = psycopg2.connect(database='comment', user='zhijia', password='1', host='35.229.80.182')
#     dbConn.set_session(autocommit=True)
#     dbCursor = dbConn.cursor()
# except (Exception, psycopg2.DatabaseError) as error:
#     print(error)
#     exit()
# commentXPaths = ObjXPATH(dbCursor)

def clkElm2ngram(elm, targetGrams, gramSize = 3):
    attribStr = ''
    for node in elm.xpath('./descendant-or-self::*[not(self::path)]'): #exclude path element because its d attribute is usually a long string which could contaminate the data
        for key, val in node.attrib.items():
            if key not in custom_attrib:
                attribStr += (val + ' ')
        if node.text:
            attribStr += (node.text + ' ')
    attribStr = attribStr.lower()
    attribStr = re.sub(r'\s+', ' ', re.sub('[^a-zA-Z]', '', attribStr))
    gramDict = {}
    gramData = [''.join(t) for t in ngrams(attribStr, gramSize)]
    for s in gramData:
        gramDict[s] = gramDict.get(s, 0) + 1

    for k in gramDict:
        gramDict[k] = gramDict[k]/len(gramData)
    
    return [gramDict.get(k, 0) for k in targetGrams]

class ButtonRawFeature:
    def __init__(self, arg):
        if isinstance(arg, list):
            self.__init1__(arg)
        else:
            self.__init2__(arg)

    def __init1__(self, pageID, gramSize = 3):
        websites = [name for name in os.listdir("./data") if os.path.isdir('./data/{}'.format(name))]
        positiveButtons = []
        negativeButtons = []
        clickableElmSet = []
        elmPageSize = []
        self.elmUrlID = []

        for id in pageID:
            for website in websites:
                fileName = "data/{website}/{id}-webpage-source.html".format(website=website, id=id)
                if os.path.isfile(fileName):
                    tree = etree.parse(open(fileName), parser)
                    body = tree.xpath('(//body)[1]')[0]
                    try:
                        position = literal_eval(body.attrib['data-position'])
                    except Exception as e:
                        continue
                    pageClickables = tree.xpath('//a|//button')
                    clickableElmSet += pageClickables
                    elmPageSize += [[position['width'], position['height']]]*len(pageClickables)
                    self.elmUrlID += [id]*len(pageClickables)
                    positiveButtons += tree.xpath(commentXPaths.commentButtonXPath[website])  # get the xpath from the database, the object located by the xpath must be either an anchor or a button
                    negativeButtons += [elm for elm in pageClickables if elm not in positiveButtons]
                    break
        # get labels
        self.y = [elm in positiveButtons for elm in clickableElmSet if 'data-position' in elm.attrib]
        
        self.rawTextFeature =[] # raw feature data from the attribute values and texts of the training objects
        self. geographicFeature = [] # element top left coordinate relative to the top left of webpage
        self.geographicFeatureLabel = ['x', 'y', 'pageWidth-x', 'pageHeight-y']
        for idx, clkElm in enumerate(clickableElmSet):
            if 'data-position' not in clkElm.attrib:
                continue # some new anchors or button may be generated after the position information is recorded
            position = literal_eval(clkElm.attrib['data-position'])
            self.geographicFeature.append([position['x']/elmPageSize[idx][0], position['y']/elmPageSize[idx][0], (elmPageSize[idx][0]-position['x'])/elmPageSize[idx][0], (elmPageSize[idx][1]-position['y'])/elmPageSize[idx][0]])
            s = ''
            for node in clkElm.xpath('./descendant-or-self::*[not(self::path)]'): #exclude path element because its d attribute is usually a long string which could contaminate the training data
                for key, val in node.attrib.items():
                    if key not in custom_attrib:
                        s += (val + ' ')
                if node.text:
                    s += (node.text + ' ')
            s = s.lower()
            s = re.sub(r'\s+', ' ', re.sub('[^a-zA-Z]', '', s))
            self.rawTextFeature.append(s)

        # generate feature data using ngram
        gramData = [[''.join(t) for t in ngrams(s, gramSize)] for s in self.rawTextFeature]
        self.X = [{} for g in gramData]
        for i, (g, d, label) in enumerate(zip(gramData, self.X, self.y)):
            for s in g:
                d[s] = d.get(s, 0) + 1
            for k in d:
                d[k] = d[k]/len(g)

    def __init2__(self, docTree, gramSize = 3):
        clickableElmSet = docTree.xpath('//a|//button')
        self.rawTextFeature =[] # raw feature data from the attribute values and texts of the training objects
        for idx, clkElm in enumerate(clickableElmSet):
            elmHTML = etree.tostring(clkElm, encoding='utf-8').decode('utf-8')
            self.rawTextFeature.append(extract_attributes(elmHTML)+extract_text(elmHTML))

        # generate feature data using ngram
        gramData = [[''.join(t) for t in ngrams(s, gramSize)] for s in self.rawTextFeature]
        self.X = [{} for g in gramData]
        for g, d in zip(gramData, self.X):
            for s in g:
                d[s] = d.get(s, 0) + 1
            for k in d:
                d[k] = d[k]/len(g)

class ButtonGramData:
    def __init__(self, pageID=None, gramSize = 3):
        self.gramSize = gramSize
        websites = [name for name in os.listdir("./data") if os.path.isdir('./data/{}'.format(name))]
        positiveButtons = []
        negativeButtons = []
        clickableElmSet = []
        self.elmUrlID = []

        for id in pageID:
            for website in websites:
                fileName = "data/{website}/{id}-webpage-source.html".format(website=website, id=id)
                if os.path.isfile(fileName):
                    tree = etree.parse(open(fileName), parser)
                    pageClickables = tree.xpath('//a|//button')
                    clickableElmSet += pageClickables
                    self.elmUrlID += [id]*len(pageClickables)
                    positiveButtons += tree.xpath(commentXPaths.commentButtonXPath[website])  # get the xpath from the database, the object located by the xpath must be either an anchor or a button
                    negativeButtons += [elm for elm in pageClickables if elm not in positiveButtons]
                    break
        self.elmHTML =  [etree.tostring(e) for e in clickableElmSet]
        
        # get labels
        self.y = [elm in positiveButtons for elm in clickableElmSet]
        
        # generate raw feature data from the attribute values and texts of the training objects
        self.rawTextFeature = []
        for clkElm in clickableElmSet:
            s = ''
            for node in clkElm.xpath('./descendant-or-self::*[not(self::path)]'): #exclude path element because its d attribute is usually a long string which could contaminate the training data
                for _, val in node.attrib.items():
                    s += (val + ' ')
                if node.text:
                    s += (node.text + ' ')
            s = s.lower()
            s = re.sub(r'\s+', ' ', re.sub('[^a-zA-Z]', '', s))
            self.rawTextFeature.append(s)

        # generate feature data using ngram
        gramData = [[''.join(t) for t in ngrams(s, gramSize)] for s in self.rawTextFeature]
        self.X = [{} for g in gramData]
        for i, (g, d, label) in enumerate(zip(gramData, self.X, self.y)):
            for s in g:
                d[s] = d.get(s, 0) + 1
            for k in d:
                d[k] = d[k]/len(g)

class ButtonTargetGramExtracter:
    """
    The ButtonTargetGramExtracter extracts the most significant gram features of the fitting ButtonGramData object/
    """
    def __init__(self, targetGramNum=10):
        self.targetGrams = None
        self.targetGramNum = targetGramNum
        self.minMaxScalar = None

    def fit(self, X, y):
        """
        The fit method first extarct the most siginificant self.targetGramNum gram features of each sample, then combine all the significant gram features of all samples and trim the set to self.targetGramNum most significant ones.
        """
        self.targetGrams = {}
        for i, (d, label) in enumerate(zip(X, y)):
            if label is True:
                dItems = sorted(list(d.items()), key=lambda x:x[1], reverse=True)
                if len(dItems) > self.targetGramNum:
                    for x in dItems[:self.targetGramNum]:
                        self.targetGrams[x[0]] = self.targetGrams.get(x[0], 0) + x[1]
                else:
                    for x in dItems:
                        self.targetGrams[x[0]] = self.targetGrams.get(x[0], 0) + x[1]
        self.targetGrams = sorted(list(self.targetGrams.items()), key=lambda x:x[1], reverse=True)
        if len(self.targetGrams) > self.targetGramNum:
            self.targetGrams = self.targetGrams[:self.targetGramNum]
        #frqSum = sum([x[1] for x in self.targetGrams])
        #if frqSum > 0:
        #    self.targetGrams = [(x[0], x[1]/float(frqSum)) for x in self.targetGrams]
        with open('pickle/button-target-grams.pickle', 'wb') as f:
            pickle.dump(self.targetGrams, f, pickle.HIGHEST_PROTOCOL)
        return self
    
    def transform(self, X, y=None):
        ret = [[d.get(x[0], 0) for x in self.targetGrams] for d in X]
        #frqSum = [sum(x) for x in ret]
        #for x, s in zip(ret, frqSum):
        #    if s > 0:
        #        x[:] = [i/float(s) for i in x]
        return ret
    
    def fit_transform(self, X, y):
        return self.fit(X, y).transform(X)

class ButtonClassifier:
    def __init__(self, website, pageNum, gramSize, dbCursor):        
        # get training objects, i.e., comment buttons and other clickable objects
        self._buttonGramData = ButtonGramData(dbCursor, website, pageNumLimit=pageNum, gramSize=gramSize) 
        trueLabelIdx = [i for i in range(len(self._buttonGramData.y)) if self._buttonGramData.y[i] is True]
        self.targetGrams = {} #target gram will only consist of first 10 most significant grams from each target sample
        significantGramNumPerSample = 10
        for i, (d, label) in enumerate(zip(self._buttonGramData.X, self._buttonGramData.y)):
            if label is True:
                dItems = sorted(list(d.items()), key=lambda x:x[1], reverse=True)
                if len(dItems) > significantGramNumPerSample:
                    for x in dItems[:significantGramNumPerSample]:
                        self.targetGrams[x[0]] = self.targetGrams.get(x[0], 0) + x[1]/len(trueLabelIdx)
                else:
                    for x in dItems:
                        self.targetGrams[x[0]] = self.targetGrams.get(x[0], 0) + x[1]/len(trueLabelIdx)
        self.targetGrams = sorted(list(self.targetGrams.items()), key=lambda x:x[1], reverse=True)
        self._buttonGramData.X = [[d.get(x[0], 0) for x in self.targetGrams] for d in self._buttonGramData.X]
        self._scaler = MinMaxScaler()
        self._buttonGramData.X = self._scaler.fit_transform(self._buttonGramData.X)

        self.X = self._buttonGramData.X
        self.y = self._buttonGramData.y
        # build classification model
        self._clf = DecisionTreeClassifier().fit(self.X, self.y)

    def _predict_preprocessing(self, predictX):
        return [[d.get(x[0], 0) for x in self.targetGrams] for d in predictX]

    def predict(self, X):
        return self._clf.predict(self._scaler.transform(self._predict_preprocessing(X)))
    
    def score(self, X, y):
        return self._clf.score(self._scaler.transform(self._predict_preprocessing(X)), y)

class ButtonNaiveFilter:
    def __init__(self, path) -> None:
        self.path = path
    
    def filter(self, keywords = ['comment']):

        truePositive = 0
        falseNegative = 0
        for f in os.listdir(os.path.join(self.path, 'positive')):
            if f.split('.')[-1] != 'html':
                continue
            falseNegative += 1
            with open(os.path.join(self.path, 'positive', f), encoding='utf-8') as fh:
                s = fh.read()
                miss = True
                for k in keywords:
                    if k in s:
                        falseNegative -= 1
                        truePositive += 1
                        miss = False
                        break
                if miss:
                    print(f'Missed button\n{s}')
                

        trueNegative = 0
        falsePositive = 0
        for f in os.listdir(os.path.join(self.path, 'negative')):
            if f.split('.')[-1] != 'html':
                continue
            trueNegative += 1
            with open(os.path.join(self.path, 'negative', f), encoding='utf-8') as fh:
                s = fh.read()
                for k in keywords:
                    if k in s:
                        trueNegative -= 1
                        falsePositive += 1
                        break
        return truePositive, falsePositive, trueNegative, falseNegative