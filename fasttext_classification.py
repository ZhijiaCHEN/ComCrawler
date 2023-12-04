import re, string, unicodedata, os, psycopg2
from os import listdir, system
from os.path import isfile, join
from nltk import ngrams
#import contractions
from bs4 import BeautifulSoup
from utility import NON_VISUAL_TAGS, NODE_HEIGHT, parse_words, custom_attrib, extract_attributes, extract_text
from lxml import etree
from io import StringIO
import pickle, random, datetime
import fasttext
from comment_classifier import CommentTextFeature
import shutil 
from statistics import mean, stdev
from style import MyElement, StyleDict
from bs4 import BeautifulSoup
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.utils import shuffle 
random.seed(datetime.datetime.now())

parser = etree.HTMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True, default_doctype=False)
parser_lookup = etree.ElementDefaultClassLookup(element=MyElement)
parser.set_element_class_lookup(parser_lookup)
webNum = 100
pageNum = 20

def get_comment_files():
    files = [f for f in os.listdir('comments') if isfile('comments/{}'.format(f))]
    ret = []
    for f in files:
        fcomp = f.split('.')
        if fcomp[1] != 'html':
            continue
        fcomp = fcomp[0].split('-')
        if len(fcomp) != 4 or fcomp[3] not in ['positive', 'negative']:
            continue
        ret.append('comments/{}'.format(f))
    return ret 

def get_comment_processed(postfix):
    files = [f for f in os.listdir('comments') if isfile('comments/{}'.format(f))]
    ret = []
    for f in files:
        fcomp = f.split('.')
        if fcomp[1] != 'txt':
            continue
        fcomp = fcomp[0].split('-')
        if len(fcomp) != 5 or fcomp[3] not in ['positive', 'negative'] or fcomp[4] != postfix:
            continue
        ret.append(f)
    return ret 

def get_999_wid():
    ret = set()
    for f in get_comment_processed('attribFile'):
        fcomp = f.split('-')
        #if fcomp[2] != '999': continue
        if fcomp[2] == '999':
            ret.add(int(fcomp[0]))
    return ret

def get_wrong_999_wid():
    w999 = get_999_wid()
    webDict = get_web_dict('attribFile')
    return [w for w in w999 if (len(webDict[w][0]), len(webDict[w][1])) in [(0,1), (1,0)]]

def get_web_dict(postfix):
    webDict = {}
    scoreDict = {}
    nTemp = {}
    pTemp = {}
    for f in get_comment_processed(postfix):
        fcomp = f.split('-')
        #if fcomp[2] != '999': continue
        if fcomp[2] == '999':
            if fcomp[3] == 'negative':
                nTemp[fcomp[0]] = nTemp.get(fcomp[0], 0) + 1
                if nTemp[fcomp[0]] > 1:
                    continue
            else:
                pTemp[fcomp[0]] = pTemp.get(fcomp[0], 0) + 1
                if pTemp[fcomp[0]] > 1:
                    continue
        
        wid = int(fcomp[0])
        if wid not in webDict:
            if fcomp[3] == 'positive':
                webDict[wid] = [[f], []]
            else:
                webDict[wid] = [[], [f]]
        else:
            if fcomp[3] == 'positive':
                webDict[wid][0].append(f)
            else:
                webDict[wid][1].append(f)
    return webDict

def tmp_move():
    for l in ['positive', 'negative']:
        files = [f for f in listdir(join('comments', l)) if isfile(join('comments', l, f)) and f.split('.')[1] == 'html']
        for f in files:
            nf = f.split('.')
            nf[0] += '-999-{}'.format(l)
            shutil.copyfile(join('comments', l, f), join('comments', '.'.join(nf)) )

def comment_preprocess_no_style():
    commentHTML = [f for f in listdir('comments') if isfile(join('comments', f)) and f.split('.')[1] == 'html']
    for fileName in commentHTML:
        try:
            with open(join('comments', fileName), encoding='utf-8') as f:
                html_doc = f.read()

                attrib = gram_text_process(parse_words(extract_attributes(html_doc)))
                attribAndText = gram_text_process(parse_words(html_doc))
                text = gram_text_process(parse_words(extract_text(html_doc)))
                
                fileNameComp = fileName.split('.')[0].split('-')
                if len(fileNameComp) != 4:
                    #print('skip file {}'.format(fileName))
                    continue
                if fileNameComp[-1] not in ['negative', 'positive']:
                    assert fileNameComp[-2] in ['negative', 'positive']
                    tmp = fileNameComp[-1]
                    fileNameComp[-1] = fileNameComp[-2]
                    fileNameComp[-2] = tmp

                textFile = join('comments', '-'.join(fileNameComp)+'-textFile.txt')
                with open(textFile, 'w', encoding='utf-8') as ft:
                    ft.write(text)
                attribAndTextFile = join('comments', '-'.join(fileNameComp)+'-attribAndTextFile.txt')
                with open(attribAndTextFile, 'w', encoding='utf-8') as fat:
                    fat.write(attribAndText)
                attribFile = join('comments', '-'.join(fileNameComp)+'-attribFile.txt')
                with open(attribFile, 'w', encoding='utf-8') as fa:
                    fa.write(attrib)
            print('preprocess: done with file {}'.format(fileName))
        except Exception as e:
            print('Failed to parse {}, removing...\n{}'.format(fileName, repr(e)))
            os.remove(join('comments', fileName))

def comment_preprocess(path):
    for label in ['positive', 'negative']:
        for fileName in os.listdir(os.path.join(path, label)):
            if fileName.split('.')[-1] != 'html':
                continue
            with open(os.path.join(path, label, fileName), encoding='utf-8') as f:
                html_doc = f.read()
                attrib = gram_text_process(extract_attributes(html_doc))
                attribFile = os.path.join(path, 'preprocessed', f'{label}-' + fileName.split('.')[0] + '.txt')
                with open(attribFile, 'w', encoding='utf-8') as fat:
                    fat.write(attrib)

def button_preprocess(path, feature='3-gram'):
    for label in ['positive', 'negative']:
        for fileName in os.listdir(os.path.join(path, label)):
            if fileName.split('.')[-1] != 'html':
                continue
            with open(os.path.join(path, label, fileName), encoding='utf-8') as f:
                html_doc = f.read()
                if feature == '3-gram':
                    attribAndText = gram_text_process(extract_attributes(html_doc) + ' ' + extract_text(html_doc))
                elif feature == 'token':
                    # attribAndText = token_text_process(extract_attributes(html_doc) + ' ' + extract_text(html_doc))
                    attribAndText = token_text_process(extract_text(html_doc))
                else:
                    raise ValueError('Invalid feature')
                attribAndTextFile = os.path.join(path, 'preprocessed', f'{label}-' + fileName.split('.')[0] + '.txt')
                with open(attribAndTextFile, 'w', encoding='utf-8') as fat:
                    fat.write(attribAndText)

def gram_text_process(text):   
    ret = parse_words(text).lower()
    ret = ''.join(ret.split())
    ret = ' '.join(''.join(t) for t in ngrams(ret, 3))
    return ret

def token_text_process(text):   
    ret = parse_words(text).lower()
    ret = ' '.join(ret.split())
    return ret

def comment_generate_train_test_data_old():
    trainRate = 0.8
    trainWid = random.sample(list(range(1, webNum+1)), int(webNum * trainRate))
    testWid = [i for i in range(1, webNum+1) if i not in trainWid]

    trainAttribAndTextFile = open('comments/train-attribute-text.txt', 'w', encoding='utf-8')
    trainAttribFile = open('comments/train-attribute.txt', 'w', encoding='utf-8')
    trainRefinedAttribFile = open('comments/train-refined-attribute.txt', 'w', encoding='utf-8')
    trainTextFile = open('comments/train-text.txt', 'w', encoding='utf-8')

    testAttribAndTextFile = open('comments/test-attribute-text.txt', 'w', encoding='utf-8')
    testAttribFile = open('comments/test-attribute.txt', 'w', encoding='utf-8')
    testRefinedAttribFile = open('comments/test-refined-attribute.txt', 'w', encoding='utf-8')
    testTextFile = open('comments/test-text.txt', 'w', encoding='utf-8')

    fileHandle = {'train':(trainAttribAndTextFile, trainAttribFile, trainRefinedAttribFile, trainTextFile), 'test':(testAttribAndTextFile, testAttribFile, testRefinedAttribFile, testTextFile)}

    for wid, fileKey in zip(trainWid+testWid, ['train']*len(trainWid)+['test']*len(testWid)):
        (attribAndTextFile, attribFile, refinedAttrib, textFile) = fileHandle[fileKey]
        for pid in range(1, pageNum+1):
            pfileName = 'comments/positive/{}-{}.html'.format(wid, pid)
            nfileName = 'comments/negative/{}-{}.html'.format(wid, pid)
            for fileName, label, s in [(pfileName, '__label__1 ', 'positive'), (nfileName, '__label__0 ', 'negative')]:
                if os.path.isfile(fileName):
                    with open('comments/{}/{}-{}-attribute-text.txt'.format(s, wid, pid), encoding='utf-8') as fat:
                        attribAndTextFile.write(label + fat.read() + '\n')

                    with open('comments/{}/{}-{}-attribute.txt'.format(s, wid, pid), encoding='utf-8') as fa:
                        attribFile.write(label + fa.read() + '\n')

                    with open('comments/{}/{}-{}-refined-attribute.txt'.format(s, wid, pid), encoding='utf-8') as fra:
                        refinedAttrib.write(label + fra.read() + '\n')

                    with open('comments/{}/{}-{}-text.txt'.format(s, wid, pid), encoding='utf-8') as ft:
                        textFile.write(label + ft.read() + '\n')

    trainAttribAndTextFile.close()
    trainAttribFile.close()
    trainTextFile.close()

    testAttribAndTextFile.close()
    testAttribFile.close()
    testTextFile.close()

def comment_generate_train_test_data(featureName, trainRate = 0.2):
    commentTxt = [f for f in listdir('comments') if isfile(join('comments', f))]
    pSample = []
    nSample = []
    pTestSample =[]
    nTemp = []
    pTemp = []
    for fileName in commentTxt:
        fcomp = fileName.split('.')
        if fcomp[-1] != 'txt': continue
        fcomp = fcomp[0].split('-')
        if fcomp[-1] != featureName: continue
        #if len(fcomp) != 5 or fcomp[-3] == '999': continue
        if len(fcomp) != 5: continue
        if fcomp[-3] == '999':
            if fcomp[-2] == 'positive':
                if fcomp[0] in pTemp:
                    continue
                else:
                    pTemp.append(fcomp[0])
            if fcomp[-2] == 'negative':
                if fcomp[0] in nTemp:
                    continue
                else:
                    nTemp.append(fcomp[0])
        if fcomp[-2] == 'positive':
            #if fcomp[-3] != '999':
            #    pTestSample.append(fileName)
            #    continue
            pSample.append(fileName)
        elif fcomp[-2] == 'negative':
            nSample.append(fileName)
        else:
            print('unexpected file: {}'.format(fileName))
            continue
    testRate = 0.3

    pTestSample = random.sample(pSample, round(testRate*len(pSample)))#+pTestSample
    nTestSample = random.sample(nSample, round(testRate*len(nSample)))
    pTrainSample = [f for f in pSample if f not in pTestSample]
    nTrainSample = [f for f in nSample if f not in nTestSample]

    testSample = pTestSample+nTestSample
    trainSample = random.sample(pTrainSample, round(trainRate*len(pTrainSample)))+random.sample(nTrainSample, round(trainRate*len(nTrainSample)))

    trainFile = open('comments/train-{}.txt'.format(featureName), 'w', encoding='utf-8')
    pTrainCnt = 0
    nTrainCnt = 0
    for trnF in trainSample:
        with open(join('comments', trnF)) as f:
            text = f.read()
            if 'positive' in trnF:
                #if len(text) < 100:
                #    print('positive train file {} has too few words, skipped'.format(trnF))
                #    continue
                label = '__label__1 '
                pTrainCnt += 1
            else:
                label = '__label__0 '
                nTrainCnt += 1
            trainFile.write(label + text + '\n')
    print('{} positive train samples and {} negative train samples.'.format(pTrainCnt, nTrainCnt))
    trainFile.close()

    testFile = open('comments/test-{}.txt'.format(featureName), 'w', encoding='utf-8')
    pTestCnt = 0
    nTestCnt = 0
    for tstF in testSample:
        with open(join('comments', tstF)) as f:
            text = f.read()
            if 'positive' in tstF:
                label = '__label__1 '
                pTestCnt += 1
            else:
                label = '__label__0 '
                nTestCnt += 1
            testFile.write(label + text + '\n')
    print('{} positive test samples and {} negative test samples.'.format(pTestCnt, nTestCnt))

def button_generate_train_test_data(testRate):
    trainRate = 1 - testRate
    samples = [f for f in os.listdir('buttons/preprocessed')]
    random.shuffle(samples)
    trainIdx = random.sample(list(range(0, len(samples))), int(trainRate*len(samples)))

    trainSamples = [samples[i] for i in trainIdx]
    testSamples = [samples[i] for i in range(0, len(samples)) if i not in trainIdx]
    
    with open('fasttext/buttons/train.txt', 'w', encoding='utf-8') as trainFile:
        for fileName in trainSamples:
            with open('buttons/preprocessed/'+fileName, encoding='utf-8') as f:
                label = '__label__{} '.format(fileName.split('-')[0])
                trainFile.write(label + f.read() + '\n')

    with open('fasttext/buttons/test.txt', 'w', encoding='utf-8') as testFile:
        for fileName in testSamples:
            with open('buttons/preprocessed/'+fileName, encoding='utf-8') as f:
                label = '__label__{} '.format(fileName.split('-')[0])
                testFile.write(label + f.read() + '\n')

def button_k_fold_cross_validation(k):
    testRate = 1/k
    trainRate = 1 - testRate
    samplesRedundancy = [f for f in os.listdir('buttons/preprocessed')]
    sampleStrSet = set()
    samples = []
    for s in samplesRedundancy:
        with open('buttons/preprocessed/'+s, encoding='utf-8') as f:
            sampleStr = f.read()
            if sampleStr in sampleStrSet:
                continue
            else:
                sampleStrSet.add(sampleStr)
                samples.append(s)
    pCnt = 0
    nCnt = 0
    for s in samples:
        if s[:8] == 'negative':
            nCnt += 1
        else:
            pCnt += 1
    N = len(samples)
    random.shuffle(samples)
    recallL = []
    precisionL = []
    for i in range(1, k+1):

        testIdx = list(range(int((i-1)/k*N), int(i/k*N)))
        trainIdx = [i for i in range(0, len(samples)) if i not in testIdx]

        testSamples = [samples[i] for i in testIdx]
        trainSamples = [samples[i] for i in trainIdx]
    
        with open('fasttext/buttons/train.txt', 'w', encoding='utf-8') as trainFile:
            for fileName in trainSamples:
                with open('buttons/preprocessed/'+fileName, encoding='utf-8') as f:
                    label = '__label__{} '.format(fileName.split('-')[0])
                    trainFile.write(label + f.read() + '\n')

        with open('fasttext/buttons/test.txt', 'w', encoding='utf-8') as testFile:
            for fileName in testSamples:
                with open('buttons/preprocessed/'+fileName, encoding='utf-8') as f:
                    label = '__label__{} '.format(fileName.split('-')[0])
                    testFile.write(label + f.read() + '\n')

        model = fasttext.train_supervised(input='fasttext/buttons/train.txt',  lr=0.5, loss='hs')
        modelName = 'fasttext/buttons/3gram.model'
        model.save_model(modelName)
        testFile = 'fasttext/buttons/test.txt'
        ret = model.test_label(testFile)
        precision = ret['__label__positive']['precision']
        recall = ret['__label__positive']['recall']
        print('Round {} precision: {}'.format(i, precision))
        print('Round {} recall: {}'.format(i, recall))
        precisionL.append(precision)
        recallL.append(recall)
    print("{}-fold cross validation precision and recall: {}, {}".format(k, mean(precisionL), mean(recallL)))

def group_k_fold(k, path):
    pFile = [f for f in os.listdir(os.path.join(path, 'positive'))]
    nFile = [f for f in os.listdir(os.path.join(path, 'negative'))]
    pX = [open(os.path.join(path, 'positive', f), encoding='utf-8').read() for f in pFile]
    nX = [open(os.path.join(path, 'negative', f), encoding='utf-8').read() for f in nFile]
    X = np.array(pX + nX)
    Y = np.array([1] * len(pX) + [0] * len(nX))
    G = np.array([int(f.split('-')[0]) for f in pFile] + [int(f.split('-')[0]) for f in nFile])
    X, Y, G = shuffle(X, Y, G)
    gKFold = GroupKFold(n_splits=k)
    return [[X[trainIndex], Y[trainIndex], X[testIndex], Y[testIndex]] for trainIndex, testIndex in gKFold.split(X, Y, G)]

def button_fasttex_HTML(path, k = 10):
    recallL = []
    precisionL = []
    i = 0
    for XTrain, YTrain, XTest, YTest in group_k_fold(10, path):
        i += 1
        with open('fasttext/button/train.txt', 'w', encoding='utf-8') as trainFile:
            for x, y in zip(XTrain, YTrain):
                label = f'__label__{y} '
                trainFile.write(label + x + '\n')

        with open('fasttext/button/test.txt', 'w', encoding='utf-8') as trainFile:
            for x, y in zip(XTest, YTest):
                label = f'__label__{y} '
                trainFile.write(label + x + '\n')
                    
        model = fasttext.train_supervised(input='fasttext/button/train.txt', lr=0.5, loss='hs', maxn=3)
        testFile = 'fasttext/button/test.txt'
        ret = model.test_label(testFile)
        precision = ret['__label__1']['precision']
        recall = ret['__label__1']['recall']
        print('Round {} precision: {}'.format(i, precision))
        print('Round {} recall: {}'.format(i, recall))
        precisionL.append(precision)
        recallL.append(recall)
    print(f"button HTML {k}-fold cross validation: precision={mean(precisionL)}({stdev(precisionL)}) and recall={mean(recallL)}({stdev(recallL)})")

def button_fasttex_attributes(path, k = 10):
    recallL = []
    precisionL = []
    i = 0
    for XTrain, YTrain, XTest, YTest in group_k_fold(10, path):
        i += 1
        with open('fasttext/button/train.txt', 'w', encoding='utf-8') as trainFile:
            for x, y in zip(XTrain, YTrain):
                label = f'__label__{y} '
                trainFile.write(label + parse_words(x) + '\n')

        with open('fasttext/button/test.txt', 'w', encoding='utf-8') as trainFile:
            for x, y in zip(XTest, YTest):
                label = f'__label__{y} '
                trainFile.write(label + parse_words(x) + '\n')
                    
        model = fasttext.train_supervised(input='fasttext/button/train.txt', lr=0.5, loss='hs', maxn=3)
        testFile = 'fasttext/button/test.txt'
        ret = model.test_label(testFile)
        precision = ret['__label__1']['precision']
        recall = ret['__label__1']['recall']
        print('Round {} precision: {}'.format(i, precision))
        print('Round {} recall: {}'.format(i, recall))
        precisionL.append(precision)
        recallL.append(recall)
    print(f"button preprocess {k}-fold cross validation: precision={mean(precisionL)}({stdev(precisionL)}) and recall={mean(recallL)}({stdev(recallL)})")

def comment_train_model(featureName):
    """
    retModel = {}
    for s in ['attribute-text', 'attribute', 'refined-attribute', 'text']:
        f = 'comments/train-{}.txt'.format(s)
        for ngram in [1, 2]:
            model = fasttext.train_supervised(input=f,  lr=0.5,  wordNgrams=ngram, loss='hs')
            modelName = 'comments/{}-{}gram.model'.format(s, ngram)
            model.save_model(modelName)
            retModel[modelName] = model
    return retModel
    """
    model = fasttext.train_supervised(input='comments/train-{}.txt'.format(featureName),  lr=0.5, loss='hs')
    modelName = 'comments/comment-section-{}.model'.format(featureName)
    model.save_model(modelName)
    return model

def button_train_model():
    model = fasttext.train_supervised(input='fasttext/buttons/train.txt', lr=0.5, loss='hs')
    modelName = 'fasttext/buttons/3gram.model'
    model.save_model(modelName)
    return model

def comment_test_model(model, featureName):
    """
    for s in ['attribute-text', 'attribute', 'refined-attribute', 'text']:
        for ngram in [1, 2]:
            modelName = 'comments/{}-{}gram.model'.format(s, ngram)
            testFile = 'comments/test-{}.txt'.format(s)
            if modelDict is None:
                model = fasttext.load_model(modelName)
            else:
                model = modelDict[modelName]
            ret = model.test(testFile)
            print('Classification using {} and {} gram: {}'.format(s, ngram,  ret[1]))
    """
    if model is None:
        model = fasttext.load_model('comments/comment-section-{}.model'.format(featureName))
    return model.test_label('comments/test-{}.txt'.format(featureName))

def button_test_model(model = None):
    if model is None:
        model = fasttext.load_model('fasttext/buttons/3gram.model')
    testFile = 'fasttext/buttons/test.txt'
    ret = model.test_label(testFile)
    for k in ret:
        print('Button classification result for label {}: {}'.format(k, ret[k]))

if __name__ == "__main__":
    button_preprocess(r"D:\Google Drive\Temple\projects\comment entry\data\comment", feature='token')