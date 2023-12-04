import random
from task import PageCollection
import os

output = os.path.join('data', 'google-vs-givewater')
with open(os.path.join(output, 'words.txt')) as f:
    words = [l.strip() for l in f]
N = 100
keys = random.sample(words, N)

with open(os.path.join(output, 'keys.txt'), 'w', encoding='utf-8') as f:
    for w in words:
        f.write(f"{w}\n")


givewaterURL = [f"https://search.givewater.com/serp?q={w}" for w in keys]
givewaterTask = PageCollection(URL=givewaterURL, output=os.path.join(output, 'givewater'), host=None)
givewaterTask.run()
givewaterTask.close_selenium()

googleURL = [f"https://www.google.com/search?q={w}&start=10" for w in keys]
googleTask = PageCollection(URL=googleURL, output=os.path.join(output, 'google'), host=None)
googleTask.run()
googleTask.close_selenium()
