from task import CheckCommentResult, DATA_PATH

task = CheckCommentResult(DATA_PATH, seleniumHost=None)
task.run()