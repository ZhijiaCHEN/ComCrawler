from xmlrpc.client import DateTime
import pandas as pd
import numpy as np
import datetime
data = pd.read_csv('data/online-test.csv').dropna()
data['date'] = [x.date() for x in pd.to_datetime(data['discovered_time'])]
data['cmt_hit'] = data['cmt_hit'].astype('bool')
data = data.drop(columns = ['discovered_time', 'last_visit_time', 'pub_time'])
sample = pd.DataFrame(data=None, columns=data.columns)
dates = sorted(data['date'].unique())
topics = data['topic'].unique()
N = 100
for d in dates[:7]:
    rows = data[data['date'] == d]
    for t in topics:
        topicRows = rows[rows['topic'] == t]
        topicProportion = len(topicRows)/len(rows)
        posRows = topicRows[topicRows['cmt_hit']]
        negRows = topicRows[~ topicRows['cmt_hit']]
        posNum = len(posRows)
        negNum = len(negRows)
        posSelect = round(posNum/len(topicRows) * topicProportion * N)
        negSelect = round(negNum/len(topicRows) * topicProportion * N)
        posSample = posRows.sample(n = posSelect)
        negSample = negRows.sample(n = negSelect)
        print(f'date: {d}, topic: {t}, # pages: {posSelect + negSelect},  # positive: {posSelect}, # negative: {negSelect}')
        sample = sample.append(posSample).append(negSample)
sample['has_cmt'] = None
sample.to_csv('data/online-test-sample.csv', index=False)
print('')