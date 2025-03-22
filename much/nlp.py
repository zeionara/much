import re

# from sklearn.feature_extraction.text import TfidfVectorizer
# from nltk import sent_tokenize, word_tokenize

import numpy as np


QUOTE_TEMPLATE = re.compile('^>+')
EXCLAMATION = re.compile('[?!]+')


def summarize(path: str, median: bool = False, min_length: int = 3, max_length: int = 10, default: str = None):
    chunks = []

    with open(path, 'r', errors = 'ignore', encoding = 'utf-8') as file:
        for line in file.readlines():
            line = line[:-1]

            if len(line) > 0:
                chunks.append(line)

    if len(chunks) < 1:
        return default

    vectorizer = TfidfVectorizer()
    vectorizer.fit(chunks)

    candidates = []

    for chunk in chunks:
        for sent in sent_tokenize(chunk):
            sent = EXCLAMATION.sub('?', sent)

            if sent.endswith('.') and not sent.endswith('..'):
                sent = sent[:-1]

            sent = QUOTE_TEMPLATE.sub('', sent)

            words = word_tokenize(sent)

            if min_length < len(words) < max_length and not sent.endswith('?') and 'http' not in sent:
                candidates.append(sent.strip())

    if len(candidates) < 1:
        return default

    scores = np.array(np.max(vectorizer.transform(candidates), axis = 1)).flatten().tolist()

    scores, candidates = zip(*sorted(zip(scores, candidates), key = lambda pair: pair[0], reverse = True))

    if median:
        if len(scores) % 2 == 0:
            summary_index = int(len(scores) / 2 - 1)
        else:
            summary_index = int((len(scores) - 1) / 2)
    else:
        summary_index = 0

    return candidates[summary_index].capitalize()
