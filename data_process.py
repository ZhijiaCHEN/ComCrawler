from datetime import datetime, timedelta
from math import factorial
from turtle import color
from matplotlib.pyplot import plot, thetagrids
import numpy
import pandas as pd
from os.path import join
import matplotlib.pyplot as plt
from lmfit.models import ExponentialModel
from lmfit import Model, Parameters, report_fit
import numpy as np
from scipy.ndimage.measurements import label
from scipy.signal.windows.windows import exponential
from scipy.special import gamma
def decay(t, tau):
    return 1/tau*np.exp(-t/tau)
def gamma_distribution(t, k, theta):
    return t**(k-1)*np.exp(-t/theta)/(theta**k*gamma(k))

def poisson_distribution(k, lmd):
    k = [int(x) for x in k]
    return np.power(lmd, k)*np.exp(-lmd)/[np.math.factorial(x) for x in k]
data = pd.read_csv(join('data', 'news_monitor.csv'), usecols=['pub_time'])
data['pub_time'] = pd.to_datetime(data['pub_time'])
#data = data[(data.pub_time > '2020-10-13 00:00:00') & (data.pub_time < '2020-10-14 00:00:00')].sort_values(by=['pub_time'])
data = data.sort_values(by=['pub_time'])[100000:110000]

time = (data.pub_time.iloc[1:]-data.pub_time.iloc[0]).astype('timedelta64[s]')
timeDiff = data['pub_time'].diff().astype('timedelta64[s]')[1:]
#print(timeDiff.values)


interval = 5
arrival = [0]*(int(time.iloc[-1]//interval) + 1)
for t in time:
    arrival[int(t//interval)] += 1

hist = [0] * (max(arrival) + 1)
for a in arrival:
    hist[a] += 1
hist = [h/sum(hist) for h in hist]

while hist[-1] < 1e-3:
    hist.pop()
print(sum(hist))
k = list(range(len(hist)))
plt.bar(k, hist, label='histogram')
# plt.show()
model = Model(poisson_distribution, independent_vars=['k'])
params = Parameters()
params.add('lmd', value=2)
#out = model.fit(hist, k=k, params=params)
lmd = sum(arrival)/len(arrival)
# yFit = poisson_distribution(k, out.best_values['lmd'])
# plt.plot(k, yFit, '-k.', label='Pois({:.2f})'.format(out.best_values['lmd']))
yFit = poisson_distribution(k, lmd)
plt.plot(k, yFit, '-k.', label='Pois({:.2f})'.format(lmd))
plt.xlabel('# arrivals per {}s'.format(interval))
plt.ylabel('probability')
plt.legend()
plt.yticks(np.arange(0, 0.35, 0.05))
plt.show()




# plt.subplot(312)
# data = pd.read_csv(join('data', 'comment_crawler.csv'))
# data['stime'] = pd.to_datetime(data['stime'])
# data['etime'] = pd.to_datetime(data['etime'])
# time = (data.etime-data.stime).astype('timedelta64[s]')
# time.sort_values()
# binNum = 100
# bins = [t/binNum*max(time) for t in range(binNum+1)] 
# cdf = plt.hist(time, bins=bins, density=True,stacked=True, label='histogram')
# #cdf = plt.hist(time, bins=bins, density=True, cumulative=True)
# t = cdf[1][:len(bins)-1]
# y = cdf[0]

# model = Model(decay, independent_vars=['t'])
# #pars = model.guess(y, t=t)
# params = Parameters()
# params.add('tau', value=2.0, min=0)
# out = model.fit(y, t=t, params=params)
# yFit = decay(t, out.best_values['tau'])
# plt.plot(t, yFit, color='k', label='Exp({:.2f})'.format(out.best_values['tau']))
# plt.xlabel('process time/s')
# plt.ylabel('probability')
# plt.yticks(np.arange(0, 0.04, 0.01))
# plt.legend()
# plt.subplot(122)
# cdf = plt.hist(time, bins=bins, density=True,stacked=True, label='histogram')
# #cdf = plt.hist(time, bins=bins, density=True, cumulative=True)
# t = cdf[1][:len(bins)-1]
# y = cdf[0]
# model = Model(gamma_distribution, independent_vars=['t'])
# #pars = model.guess(y, t=t)
# params = Parameters()
# params.add('k', value=2.0, min=1)
# params.add('theta', value=2.0, min=0)
# out = model.fit(y, t=t, params=params)
# yFit = gamma_distribution(t, out.best_values['k'], out.best_values['theta'])
# plt.plot(t, yFit, color='k', label='$\Gamma$({:.2f}, {:.2f})'.format(out.best_values['k'], out.best_values['theta']))
# plt.xlabel('process time/s')
# plt.ylabel('probability')
# plt.yticks(np.arange(0, 0.04, 0.01))
# plt.legend()
# plt.tight_layout()
# plt.show()

