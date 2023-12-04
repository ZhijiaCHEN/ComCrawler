from datetime import datetime
from matplotlib.pyplot import thetagrids
import pandas as pd
from os.path import join
import matplotlib.pyplot as plt
from lmfit.models import ExponentialModel
from lmfit import Model, Parameter, report_fit
import numpy as np
def decay(t, tau):
    return np.exp(-t/tau)
data = pd.read_csv(join('data', 'comment_crawler.csv'))
data['stime'] = pd.to_datetime(data['stime'])
data['etime'] = pd.to_datetime(data['etime'])
time = (data.etime-data.stime).astype('timedelta64[s]')
time.sort_values()
bins = list(range(301))
cdf = plt.hist(time, bins=bins, cumulative=-1, density=True)
t = cdf[1][:len(bins)-1]
y = cdf[0]
model = Model(decay, independent_vars=['t'])
#pars = model.guess(y, t=t)
out = model.fit(y, t=t, tau=1)
yFit = decay(t, out.best_values['tau'])
plt.plot(t, yFit)
plt.show()

