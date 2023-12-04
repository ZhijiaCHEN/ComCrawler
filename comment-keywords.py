from googletrans import Translator, LANGCODES
import time
translator = Translator()
keywordsEN = ['comment', 'reply', 'discuss', 'discussion']
keywords = []
for code in LANGCODES:
    for word in keywordsEN:
        rslt = translator.translate(word, dest=code)
        while rslt._response.status_code == 429:
            print('Get blocked. Going to sleep for 10 minutes.')
            time.sleep(600)
            rslt = translator.translate(word, dest=code)
        keywords.append(rslt.text)
        print(f'Translate {word} into {code}: {rslt.text}')
        time.sleep(10)

keywords = set(keywords)
with open('keywords.txt', 'w', encoding='utf-8') as f:
    f.write(','.join(keywords))
