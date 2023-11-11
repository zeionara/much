from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .util import SPACE, normalize


MENTION_TEMPLATE = re.compile('>>[0-9]+')
OP_TEMPLATE = re.compile(r'\(OP\)>?')
EMPTY = ''
MIN_POST_LENGTH = 0

POST_ID_TEMPLATE = re.compile('m[0-9]{4,}')


def post_id_to_int(post_id: str):
    return int(post_id[1:])


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

    @property
    def size(self):
        return len(self.text)

    @classmethod
    def from_body(cls, body: BeautifulSoup, html: BeautifulSoup = None, key = None):
        body_text = None if body is None else body.get_text(separator = SPACE)
        text = normalize(MENTION_TEMPLATE.sub(SPACE, OP_TEMPLATE.sub(SPACE, EMPTY if body_text is None else body_text)))
        if len(text) < MIN_POST_LENGTH:
            return None, None

        if key is None:
            try:
                key = None if body is None else post_id_to_int(body['id'])
            except KeyError:
                key = None
            except ValueError:
                key = post_id_to_int(POST_ID_TEMPLATE.findall(str(body))[0])

        # print(html)

        mentions = None if html is None else html.find_all('a', {'class': 'post-reply-link'})

        if mentions is not None:
            mentions = [int(mention['data-num']) for mention in mentions]

        # for mention in html.find('div', id=f'refmap-{key}').find_all('a', {'class': 'post-reply-link'}):
        #     print(mention['data-num'])

        return mentions, cls(text = text, id = key)

    @classmethod
    def from_html(cls, html: BeautifulSoup):
        body = html.find("blockquote")

        if body is None:
            body = html.find('article')

        if body is None:
            body = html.find('div', {'class': 'post_comment_body'})

        key = html.get('postid')

        return cls.from_body(body, html, key = None if key is None else int(key))
