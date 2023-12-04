from logging import debug
from nltk.tag import pos_tag_sents
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from postgres import Postgres
from task import CheckCrawlerWithoutQueue, NaiveCommentCrawler, NewsMonitor, ButtonCrawlerXpath, CollectXPath, DATA_PATH
import os



# t = CollectXPath(seleniumHost=None,  debug=True)
# t.run()

t = ButtonCrawlerXpath(seleniumHost=None, output='D:\\Google Drive\\Temple\\projects\\comment entry\\data\\button-new', N=20, debug=True)
t.run()
# a = ArticleCrawler(host = 'database')
# a.run_once()
# from statistics import mean, stdev
# T = {}
# db = Postgres()
# db.cursor.execute('select aid, stime, etime from comment_crawler order by stime')
# for r in db.cursor.fetchall():
#     (aid, stime, etime) = tuple(r)
#     t = etime - stime
#     t = t.seconds + t.microseconds/1e6
#     if t > 120:
#         continue
#     T.setdefault(aid, []).append(t)
# for i in range(3):
#     sample = [T[aid][i] for aid in T if len(T[aid]) == 3]
#     print('round {} mean: {}, std: {}'.format(i+1, mean(sample), stdev(sample)))




# task = NaiveCommentCrawler(seleniumHost=None, debug = True)
# task.run()
# #driver.set_window_size(1920, 1080)
# task = GetLanguageRegion(driver)
# task.run()