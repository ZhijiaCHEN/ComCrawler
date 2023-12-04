import dateparser
import os, re
from lxml import etree
parser = etree.HTMLParser(encoding='utf-8', remove_comments=True)
pPath = r'G:\My Drive\Temple\projects\comment entry\data\comment\positive'
nPath = r'G:\My Drive\Temple\projects\comment entry\data\comment\negative'
TP = TN = FP = FN = 0
IS_NUMBER = 1
IS_ALPHA = 2
def signature(sList):
    ret = []
    for s in sList:
        i = 0
        signature = []
        while i < len(s):
            if s[i].isdigit():
                j = i + 1
                while j < len(s):
                    if s[j].isdigit():
                        j += 1
                    else:
                        break
                i = j
                signature.append(IS_NUMBER)
            elif s[i].isalpha():
                j = i + 1
                while j < len(s):
                    if s[j].isalpha():
                        j += 1
                    else:
                        break
                i = j
                signature.append(IS_ALPHA)
            else:
                j = i + 1
                while j < len(s):
                    if not s[j].isdigit() and not s[j].isalpha():
                        j += 1
                    else:
                        break
                i = j
                signature.append(0)
        ret.append(tuple(signature))
    return tuple(ret)

def is_datetime(signature2s, label):
        ret = False
        candidate = None
        for signature, candidate in signature2s.items():
            if len(candidate) < 5 or len([x for y in signature for x in y]) <= 1:
                continue
            datetimeS = [y for y in [dateparser.parse(x) for x in candidate] if y is not None]
            # ret = max(ret, len(datetimeS))
            if len(datetimeS) >= 5:
                ret = True
                break
        if ret != label:
            if label:
                print(f'False Negative:')
                for k, v in signature2s.items():
                    if len(v) >= 5:
                        print(f'\t{k=}, {v=}\n')
            else:
                print(f'False Positive: {candidate}.')
        return ret

def build_signature_dict(file):
    tree = etree.parse(file, parser=parser)
    leaves = tree.xpath('//*[not(child::*)]')
    minLen = 2
    texts = [z for z in [re.sub('\s+', ' ', y.strip()) for y in [x.text for x in leaves if x.text and len(x.text) >= minLen]] if 30 >= len(z) >= minLen]
    signature2s = {}
    for s in texts:
        frag = re.split('-/,: ', s)
        signature2s.setdefault(signature(frag), []).append(s)
    return signature2s
if __name__ == '__main__':
    for f in os.listdir(pPath):
        if f.split('.')[-1] != 'html':
            continue
        #f = '78-2.html'
        print(f'Classifying positive page {f}.')
        file = os.path.join(pPath, f)
        signature2s = build_signature_dict(file)

        if is_datetime(signature2s, True):
            TP += 1
        else:
            FN += 1

    for f in os.listdir(nPath):
        if f.split('.')[-1] != 'html':
            continue
        print(f'Classifying negative page {f}.')
        file = os.path.join(nPath, f)
        signature2s = build_signature_dict(file)
        
        if is_datetime(signature2s, False):
            FP += 1
        else:
            TN += 1

    print(f'{TP=}, {TN=}, {FP=}, {FN=}.')