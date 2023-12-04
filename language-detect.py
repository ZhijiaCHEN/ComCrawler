import os
from langdetect import detect
from bs4 import BeautifulSoup
import re, pickle

from six import with_metaclass
path = "D:\Google Drive\Temple\projects\comment entry\data\comment\positive"
blacklist = [
    'document',
   'noscript',
    'header',
    'html',
    'meta',
    'head', 
    'input',
    'script']

wid2lan = {}

for file in os.listdir(path):
    with open(os.path.join(path, file), encoding='utf-8') as f:
        wid = int(file.split("-")[0])
        wid2lan.setdefault(wid, {})
        html = f.read()
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text = re.sub(r' +', ' ', text.replace('\n', ' ').replace('\t', ' '))
        if len(text) < 3:
            print('no text in file {}'.format(file))
            continue
        lan = detect(text)
        wid2lan[wid][lan] = wid2lan[wid].setdefault(lan, 0) + 1
lanCnt = {}
for key, val in list(wid2lan.items()):
    lanFreq = sorted(list(val.items()), key=lambda x:x[1], reverse=True)
    if len(lanFreq) > 1:
        print(lanFreq)
    wid2lan[key] = lanFreq[0][0]
    lanCnt[wid2lan[key]] = lanCnt.setdefault(wid2lan[key], 0) + 1

with open('language-detect.pickle', 'wb') as f:
    pickle.dump((wid2lan, lanCnt), f)





