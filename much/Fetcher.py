from requests import get
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .Post import Post


@dataclass
class Topic:
    title: str
    comments: tuple[str]


class Fetcher:
    def __init__(self):
        pass

    def fetch(self, url: str):
        # print(f'Pulling data from {url}...')

        id_to_post = {}
        ids = set()

        response = get(url)

        page = response.text

        soup = BeautifulSoup(page, features = 'html.parser')

        def append_post(post):
            mentions, post = Post.from_html(post)

            if post is None:
                return

            ids.add(post.id)

            id_to_post[post.id] = post

            if mentions is not None:
                for mention in mentions:
                    if mention in id_to_post:
                        id_to_post[mention].append(post)
                    # else:
                    #     print(f'No mention {mention}')

        # posts = soup.find_all('blockquote', {'class': 'post-message'})

        append_post(soup.find('div', {'class': ('post', 'oppost')}))

        # posts = soup.find_all('div', {'class': 'post reply'})
        # for post in soup.select('div[class*="post reply"]'):
        for post in soup.find_all('div', {'class': ('post', 'reply')}):
            append_post(post)

            # mention, post = Post.from_html(post)

            # if post is None:
            #     continue

            # id_to_post[post.id] = post

            # if mention is not None:
            #     if mention in id_to_post:
            #         id_to_post[mention].append(post)
            #     else:
            #         print(f'No mention {mention}')

        # print(id_to_post[181770267])

        topics = []

        for post in sorted(id_to_post.values(), key = lambda post: (post.length, len(post.text)), reverse = True):

            # for mention in post.mentions:
            #     if mention.text == 181771392:
            #         print(post)

            if post.id in ids:
                # print(post.describe(ids))
                # print()

                comments = []

                for mention in post.mentions:
                    if mention.id in ids:
                        ids.remove(mention.id)
                        comments.append(mention.text)

                topics.append(
                    Topic(
                        title = post.text,
                        comments = comments
                    )
                )

                ids.remove(post.id)

            if len(ids) < 1:
                break

        return topics
        # print(len(ids))
