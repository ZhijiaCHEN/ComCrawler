from textdistance import jaro_winkler
from lxml import etree
from io import StringIO
from utility import *
import psycopg2
from selenium import webdriver
from types import SimpleNamespace
from style import StyleDict, MyElement
import re, random
from math import log
from nltk import ngrams, word_tokenize
import pickle
from datetime import datetime

random.seed(datetime.now())

class CommentStructureFeature:
    def __init__(self, styleDict, simThresh = 0.75, shortTextThresh = 20):
        head = styleDict.headNode
        tail = styleDict.tailNode
        endIdx = max(k for k in tail.position.keys())
        self.treeHeight = int(tail.position[endIdx].treeNode.attrib[NODE_HEIGHT])
        self.heightCnt = [0]*(self.treeHeight+1)
        subtreePattern = [[] for i in range(self.treeHeight+1)]
        self.leafDepthDistribution = {}
        
        numberTextCnt = 0
        self.shortTextNumber = 0

        for k in sorted(list(styleDict.keys()), key=lambda x:x[1]):
            sNode = styleDict[k]
            position = [p for p in sNode.position if sNode.position[p].startStyle]

            while len(position) > 0:
                s1 = sNode.position[position.pop()]
                for s2Position in [p for p in position]:
                    s2 = sNode.position[s2Position]
                    match = True
                    if tuple_similarity(s1.attributeValues, s2.attributeValues) > simThresh and len(s1.treeNode) == len(s2.treeNode):
                        childMismatch = 0
                        for child1, child2 in zip(s1.treeNode, s2.treeNode):
                            if child1.position.match != child2.position.match:
                                childMismatch += 1
                        if len(s1.treeNode) > 0 and childMismatch/len(s1.treeNode) > 0.5:
                            match = False
                    else:
                        match = False
                    if match:
                        s1.match.append(s2)
                        s2.match = s1.match
                        position.remove(s2Position)

        currentIdx = 0
        thisNode = head
        styleHeightCntDict = {}
        styleHeightCnt = 0
        #self.styles = []
        while thisNode:
            height = int(thisNode.position[currentIdx].treeNode.attrib[NODE_HEIGHT])
            self.heightCnt[height] += 1
            if thisNode.position[currentIdx].match not in subtreePattern[height]:
                #self.styles.append(thisNode.position[currentIdx].match)
                subtreePattern[height].append(thisNode.position[currentIdx].match)
                if len(thisNode.position[currentIdx].match) > 5:
                    numberTextCnti = 0
                    for n in thisNode.position[currentIdx].match:
                        if n.treeNode.text:
                            text = ''.join(n.treeNode.text.split())
                            if len(text) > 1 and len(text) < shortTextThresh:
                                #shortTextCnti += 1
                                m = re.search('\d', text)
                                if m:
                                    numberTextCnti += 1
                                #    print('get short text with number: {}'.format(text))
                                #else:
                                #    print('get short text without number: {}'.format(text))

                        elif n.treeNode.tail:
                            tail = ''.join(n.treeNode.tail.split())
                            if len(tail) > 1 and len(tail) < shortTextThresh:
                                #shortTextCnti += 1
                                m = re.search('\d', tail)
                                if m:
                                    numberTextCnti += 1
                                #    print('get short text with number: {}'.format(tail))
                                #else:
                                #    print('get short text without number: {}'.format(tail))
                    if numberTextCnti > 0:
                        numberTextCnt += numberTextCnti
                        self.shortTextNumber += numberTextCnti*numberTextCnti/len(thisNode.position[currentIdx].match)
                pNode = thisNode.position[currentIdx].treeNode.getparent()
                if pNode and len(pNode.position.match) == 1:
                    styleHeightCnt += 1
                    styleHeightCntDict[height] = styleHeightCntDict.get(height, 0) + 1
            thisNode = thisNode.position[currentIdx].nextNode
            currentIdx += 1
        if styleHeightCnt > 0:
            if styleHeightCnt == 1:
                self.styleHeightEntropy = 0
            else:
                self.styleHeightEntropy = sum([abs(styleHeightCntDict[h]/styleHeightCnt*log(styleHeightCntDict[h]/styleHeightCnt)/log(styleHeightCnt)) for h in styleHeightCntDict])
        else:
            self.styleHeightEntropy = 1
        leaves = styleDict.etree.xpath('//*[not(*)]')
        for n in leaves:
            depth = len(n.xpath('./ancestor::*'))
            self.leafDepthDistribution[depth] = self.leafDepthDistribution.get(depth, 0) + 1/len(leaves)

        self.subtreeStyleEntropy = [sum([abs(len(pattern)/count*log(len(pattern)/count)/log(count)) if count > 1 else 0 for pattern in patterns]) for patterns,count in zip(subtreePattern, self.heightCnt)]
        self.heightDistribution = [x/(endIdx+1) for x in self.heightCnt]
        if self.shortTextNumber > 0:
            self.shortTextNumber = self.shortTextNumber / numberTextCnt

    @property
    def structure_feature(self):
        L = 5
        if len(self.subtreeStyleEntropy) > L:
            self.subtreeStyleEntropy = self.subtreeStyleEntropy[:L]
        else:
            self.subtreeStyleEntropy = self.subtreeStyleEntropy + [0] * (L - len(self.subtreeStyleEntropy))
        
        if len(self.heightDistribution) > L:
            self.heightDistribution = self.heightDistribution[:L]
        else:
            self.heightDistribution = self.heightDistribution + [0] * (L - len(self.heightDistribution))

        return self.subtreeStyleEntropy + self.heightDistribution + [self.shortTextNumber, self.styleHeightEntropy]

class CommentTextFeature:
    def __init__(self, styleDictOrEtree):
        s = ''
        if type(styleDictOrEtree) == StyleDict:
            for k in styleDictOrEtree:
                sNode = styleDictOrEtree[k]
                if len(sNode.position) >= 5:
                    for _, node in sNode.position.items():
                        s += ''.join(node.attributeValues)
        else:
            positionSeen = []
            for elm in styleDictOrEtree.xpath('.//*'):
                elmPosition = elm.position.node.position
                if len(elmPosition) >= 5 and elmPosition not in positionSeen:
                    for _, node in elmPosition.items():
                        s += ''.join(node.attributeValues)
                    positionSeen.append(elmPosition)
            
        s = s.lower()
        s = ''.join(parse_words(s).split())
        self.preprocessedText = ' '.join(''.join(t) for t in ngrams(s, 3))

        #self.preprocessedText = parse_words(s)
        self.gramFrequency = {}
        #for gram in [' '.join(t) for t in ngrams(word_tokenize(s), 2)]:
        for gram in word_tokenize(self.preprocessedText):
            self.gramFrequency[gram] = self.gramFrequency.get(gram, 0) + 1
        for k in self.gramFrequency:
            self.gramFrequency[k] = self.gramFrequency[k]/len(self.gramFrequency)
    def target_gram_feature(self, targetGrams):
        ret = [self.gramFrequency[g] if g in self.gramFrequency else 0 for g in targetGrams]
        #s = sum(ret)
        #if s > 0:
        #    ret = [v/s for v in ret]
        return ret