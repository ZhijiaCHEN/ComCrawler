from task import NaiveCommentCrawler, SeleniumTask

task = NaiveCommentCrawler(seleniumHost=None, databaseHost='localhost')
task.run()