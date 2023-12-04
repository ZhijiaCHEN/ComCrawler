"""
This script detects structured contents in comments samples with frequent subtree mining.
"""
from ast import parse
from io import StringIO
from lxml import etree
from style import StyleDict, MyElement, MyParser
from os import path, listdir
from utility import *
import pickle

parser_lookup = etree.ElementDefaultClassLookup(element=MyElement)
parser = etree.HTMLParser(remove_blank_text=True, remove_comments = True)
parser.set_element_class_lookup(parser_lookup)

cmtPath = 'D:\Google Drive\Temple\projects\comment entry\data\comment\positive'
comments = listdir(cmtPath)
failure = []
success = []

def visit_elm(eElm, structEtreeElm, minHeight=3):
    minCmtDepth = 5
    if len(eElm.xpath('./ancestor-or-self::*')) <= minCmtDepth:
        return
    if int(eElm.attrib[NODE_HEIGHT]) <= minHeight: return True
    freqThresh = 5
    for child in eElm:
        if (eElm.tag != 'body') and len(child.position.match) >= freqThresh and int(child.attrib[NODE_HEIGHT]) >= minHeight:
            structEtreeElm.append(eElm)
            return True

parser = MyParser()
for cmt in comments:
    structEtreeElm = []
    with open(path.join(cmtPath, cmt), encoding='utf-8') as f:
        cmtEtree = etree.parse(StringIO(f.read()), parser)
        cmtFreqDict = StyleDict(cmtEtree)
        pre_order_traversal(cmtEtree.getroot(), visit_elm, structEtreeElm)
        if len(structEtreeElm) > 0:
            success.append(cmt)
        else:
            failure.append(cmt)

with open('comment_structure_detection.pickle', 'wb') as f:
    pickle.dump({'success': success, 'failure': failure}, f)

