from traceback import print_exc

from requests import get
from requests.exceptions import SSLError, ConnectionError, ChunkedEncodingError, ReadTimeout
from dataclasses import dataclass
from time import sleep

from bs4 import BeautifulSoup
from numpy import percentile

from .Post import Post, MissingPostIdException
from .util import pure_spaces, normalize, make_ordinal


POST_SIZE_PERCENTILE = 15
SSL_ERROR_DELAY = 1  # seconds

# BLOCKED_KEYWORD = (
#     '<h3>Заблокировано по требованию Роскомнадзора.<br><p style="font-size:50%">'
#     'P.S. Используйте <a href="http://arhivachqqqvwqcotafhk4ks2he56seuwcshpayrm5myeq45vlff44yd.onion/thread/860">Tor версию</a>.</p></h3>'
# )
BLOCKED_KEYWORD = '<h3>Заблокировано по требованию Роскомнадзора.<br><p style="font-size:50%">P.S. Используйте'
BLOCKED_KEYWORD_2 = '<h3>Заблокировано по жалобам третьих лиц.<br><p style="font-size:50%">P.S. Используйте'
BLOCKED_KEYWORD_3 = '<h3>Заблокировано по жалобам третьих лиц.</h3>'
TOO_LARGE = '<h3>Тред слишком большой для отображения на одной странице.<br>Мы работает над решением.'


@dataclass
class Topic:
    title: str
    comments: tuple[str]

    def find(self, title: str):
        if self.title.startswith(title):
            return self.title

        for comment in self.comments:
            if comment.startswith(title):
                return comment

        return None


class Fetcher:
    def __init__(self):
        pass

    def fetch(self, url: str, verbose: bool = False):
        if verbose:
            print(f'Pulling data from {url}...')

        id_to_post = {}
        ids = set()

        post_sizes = []
        min_post_length = 0  # later this value is inferred using percentile defined above

        def append_post(post):
            if post is None:
                # print(f'Post is none for url {url}')
                return None

            try:
                mentions, post = Post.from_html(post)
            except MissingPostIdException:
                return False
            except Exception:
                print(f'Can\'t handle post {url}')
                raise

            if post is None or pure_spaces(post.text):
                return False

            post_sizes.append(post.size)

            ids.add(post.id)

            id_to_post[post.id] = post

            if mentions is not None:
                for mention in mentions:
                    if mention in id_to_post:
                        id_to_post[mention].append(post)
                    # else:
                    #     print(f'No mention {mention}')

            return True

        def append_mentions(post: Post, comments: list, depth: int = 1):
            for mention in post.mentions:
                if mention.id in ids:
                    ids.remove(mention.id)
                    # comments.append('>' * depth + ' ' + mention.text)
                    comments.append(mention)
                    append_mentions(mention, comments = comments, depth = depth + 1)

        if url.endswith('json'):
            raise ValueError('JSON links are not supported')

        response = None

        i = 0

        while response is None or (response is not True and (response.status_code != 200 or (len(response.text) < 1))):
            i += 1

            if url.startswith('http'):
                try:
                    response = get(url, timeout = 60)
                except SSLError:
                    print(f'Encountered SSLError when fetching {url}. Waiting for {SSL_ERROR_DELAY} seconds before retrying...')
                    sleep(SSL_ERROR_DELAY)
                    print(f'Retrying to fetch {url}...')
                    continue
                except ConnectionError:
                    print(f'Encountered ConnectionError when fetching url {url}. Waiting for {SSL_ERROR_DELAY} seconds before retrying...')
                    sleep(SSL_ERROR_DELAY)
                    print(f'Retrying to fetch url {url}')
                    continue
                except ChunkedEncodingError:
                    print(f'Encountered ChunkedEncodingError when fetching url {url}. Waiting for {SSL_ERROR_DELAY} seconds before retrying...')
                    sleep(SSL_ERROR_DELAY)
                    print(f'Retrying to fetch url {url}')
                    continue
                except ReadTimeout:
                    print(f'Encountered ReadTimeout when fetching url {url}. Waiting for {SSL_ERROR_DELAY} seconds before retrying...')
                    sleep(SSL_ERROR_DELAY)
                    print(f'Retrying to fetch url {url}')
                    continue

                if response is None:
                    print(f'Got none response when fetching url {url}. Waiting for {SSL_ERROR_DELAY} seconds before retrying...')
                    sleep(SSL_ERROR_DELAY)
                    print(f'Retrying to fetch url {url}')
                    continue

                page = response.text
            else:
                with open(url, 'r', encoding = 'utf-8') as file:
                    page = file.read()
                    response = True

            soup = BeautifulSoup(page, features = 'html.parser')

            if append_post(soup.find('div', {'class': ('post', 'oppost')})) is None:
                response = None

                found_keyword = False
                for keyword in (
                    '<h3>Здесь ничего нет.</h3>',
                    '<span class="nf__nf">404</span>',
                    BLOCKED_KEYWORD,
                    '<h3>Тред скрыт. Скорее всего, он содержит нежелательный контент.</h3>', '<i class="icon-refresh icon-white"></i>',
                    BLOCKED_KEYWORD_2,
                    BLOCKED_KEYWORD_3,
                    TOO_LARGE
                ):
                    # if keyword == BLOCKED_KEYWORD:
                    #     print(BLOCKED_KEYWORD)
                    #     print(page)
                    if keyword in page:
                        # print(f'Skipping because the page contains {keyword}')
                        found_keyword = True
                        break

                if found_keyword:
                    print(f"🔵 Can't find oppost in '{normalize(page)[:100]}'. Skipping...")
                    break

                print(f"🔴 Can't find oppost in '{normalize(page)[:100]}'. Waiting for {SSL_ERROR_DELAY} seconds before retrying...")
                sleep(SSL_ERROR_DELAY)
                print(f'🟡 Retrying ({make_ordinal(i + 1)} attempt to fetch {url})...')

        for post in soup.find_all('div', {'class': ('post', 'reply')}):
            append_post(post)

        min_post_length = 0 if len(post_sizes) < 1 else int(percentile(post_sizes, POST_SIZE_PERCENTILE))

        topics = []

        for post in sorted(id_to_post.values(), key = lambda post: (post.length, -post.n_parents, len(post.text)), reverse = True):

            if post.id in ids and post.size >= min_post_length:

                # print(post.length, post.text, post.n_parents)

                # if post.id == 52234659:
                #     print(post.short_description)

                #     for mention in post.mentions:
                #         print(mention.short_description)

                comments = []

                append_mentions(post, comments = comments)

                # for mention in post.mentions:
                #     if mention.id in ids:
                #         ids.remove(mention.id)
                #         comments.append(mention.text)

                #         for mention in mention.mentions:
                #             if mention.id in ids:
                #                 ids.remove(mention.id)
                #                 comments.append(mention.text)

                topics.append(
                    Topic(
                        title = post.text,
                        comments = tuple(comment.text for comment in comments if comment.size >= min_post_length)
                    )
                )

                if post.id in ids:  # might have been removed in append_mentions?
                    ids.remove(post.id)

            if len(ids) < 1:
                break

        return topics
        # print(len(ids))
