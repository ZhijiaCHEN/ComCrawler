
from task import CountCommentNumber, NaiveCommentCrawler, NewsMonitor, CheckCommentResult, DATA_PATH

task = CountCommentNumber(DATA_PATH, seleniumHost=None, databaseHost='7.222.242.74')
task.run()
