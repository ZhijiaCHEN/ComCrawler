from distutils.log import debug
from task import CommentCrawler

c = CommentCrawler(seleniumHost=None, browser='chrome', debug=False)
c.run()