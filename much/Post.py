from __future__ import annotations

import re

from bs4 import BeautifulSoup


MENTION_TEMPLATE = re.compile('>>[0-9]+')
OP_TEMPLATE = re.compile(r'\(OP\)>?')
MIN_POST_LENGTH = 100


class Post:
    def __init__(self, text: str, id: str, mentions: list[Post] = None):
        self.text = text
        self.id = id
        self.mentions = [] if mentions is None else mentions

    def __repr__(self):
        return self.description

    def append(self, mention: Post):
        self.mentions.append(mention)

    @property
    def short_description(self):
        return f'{self.text} @ {self.id}'

    @property
    def description(self):
        return self.describe()

    def describe(self, ids: set[int] = None):
        mentions = self.mentions if ids is None else [mention for mention in self.mentions if mention.id in ids]

        return self.short_description + (
            '' if len(self.mentions) < 1 else ' '.join([f'> {mention.short_description}' for mention in mentions])
        )

    @property
    def length(self):
        return len(self.mentions)

    @classmethod
    def from_html(cls, html: BeautifulSoup):
        body = html.find('blockquote')

        text = MENTION_TEMPLATE.sub(' ', OP_TEMPLATE.sub(' ', body.text)).strip()
        if len(text) < MIN_POST_LENGTH:
            return None, None

        key = int(body['id'][1:])

        # print(html)

        mentions = html.find_all('a', {'class': 'post-reply-link'})

        if mentions is not None:
            mentions = [int(mention['data-num']) for mention in mentions]

        # for mention in html.find('div', id=f'refmap-{key}').find_all('a', {'class': 'post-reply-link'}):
        #     print(mention['data-num'])

        return mentions, cls(text = text, id = key)
