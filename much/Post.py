from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .util import SPACE, normalize


MENTION_TEMPLATE = re.compile('>>[0-9]+')
OP_TEMPLATE = re.compile(r'\(OP\)>?')
EMPTY = ''
MIN_POST_LENGTH = 0

MENTION_TEMPLATE = re.compile(r'>>([0-9]+)(\s+\(OP\)\s*)?')
POST_ID_TEMPLATE = re.compile('m[0-9]{4,}')
POST_ID_HEAD_TEMPLATE = re.compile('([0-9]+).*', re.DOTALL)


class MissingPostIdException(Exception):
    pass


def post_id_to_int(post_id: str):
    return int(post_id[1:])


def parse_mention(mention: BeautifulSoup):
    match = MENTION_TEMPLATE.fullmatch(mention.text)

    if match is None:
        return None

    return int(match.group(1))


def parse_post_id(post_id: str):
    if post_id is None or len(post_id) < 1:
        return None

    try:
        return int(post_id)
    except ValueError:
        match = POST_ID_HEAD_TEMPLATE.fullmatch(post_id)

        # if post_id == '169</div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\n\t\t\t\t\n\t\t\t\t\t\t\n\t\t\t\t\t\t\t<div id=':
        #     print(match)

        if match is None:
            return None

        return int(match.group(1))


class Post:
    def __init__(self, text: str, id: str, mentions: list[Post] = None, n_parents: int = 0):
        self.text = text
        self.id = id
        self.mentions = [] if mentions is None else mentions
        self.n_parents = n_parents

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

        # if key == 52234659:
        #     print(body)
        #     print(html)

        if key is None:
            try:
                key = None if body is None else post_id_to_int(body['id'])
            except KeyError:
                key = None
            except ValueError:
                id_matches = POST_ID_TEMPLATE.findall(str(body))
                if len(id_matches) < 1:
                    raise MissingPostIdException(f'{id_matches}')
                key = post_id_to_int(id_matches[0])

        # print(html)

        # mentions = None if html is None else html.find_all('a', {'class': 'post-reply-link'})
        # if mentions is not None:
        #     mentions = [int(mention['data-num']) for mention in mentions]

        if html is None:
            mentions = None
        else:
            mentions = []

            for link in html.find_all('a'):
                mention = parse_mention(link)
                if mention is not None:
                    mentions.append(mention)

        # for mention in html.find('div', id=f'refmap-{key}').find_all('a', {'class': 'post-reply-link'}):
        #     print(mention['data-num'])

        return mentions, cls(text = text, id = key, n_parents = 0 if mentions is None else len(mentions))

    @classmethod
    def from_html(cls, html: BeautifulSoup):
        body = html.find("blockquote")

        if body is None:
            body = html.find('article')

        if body is None:
            body = html.find('div', {'class': 'post_comment_body'})

        key = html.get('postid')

        return cls.from_body(body, html, key = parse_post_id(key))
