from requests import get
from dataclasses import dataclass

from bs4 import BeautifulSoup
from numpy import percentile

from .Post import Post
from .util import pure_spaces


POST_SIZE_PERCENTILE = 15


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

    def fetch(self, url: str):
        # print(f'Pulling data from {url}...')

        id_to_post = {}
        ids = set()

        post_sizes = []
        min_post_length = 0  # later this value is inferred using percentile defined above

        def append_post(post):
            if post is None:
                print(f'Post is none for url {url}')
                return

            try:
                mentions, post = Post.from_html(post)
            except Exception as e:
                print(f'Can\'t handle post {url}')
                raise

            if post is None or pure_spaces(post.text):
                return

            post_sizes.append(post.size)

            ids.add(post.id)

            id_to_post[post.id] = post

            if mentions is not None:
                for mention in mentions:
                    if mention in id_to_post:
                        id_to_post[mention].append(post)
                    # else:
                    #     print(f'No mention {mention}')

        def append_mentions(post: Post, comments: list, depth: int = 1):
            for mention in post.mentions:
                if mention.id in ids:
                    ids.remove(mention.id)
                    # comments.append('>' * depth + ' ' + mention.text)
                    comments.append(mention)
                    append_mentions(mention, comments = comments, depth = depth + 1)

        if url.endswith('html'):
            response = get(url)

            page = response.text

            soup = BeautifulSoup(page, features = 'html.parser')

            append_post(soup.find('div', {'class': ('post', 'oppost')}))

            for post in soup.find_all('div', {'class': ('post', 'reply')}):
                append_post(post)
        elif url.endswith('json'):
            # response = get(url)

            # page = response.json()

            # print(page)

            raise ValueError('JSON links are not supported')

        min_post_length = 0 if len(post_sizes) < 1 else int(percentile(post_sizes, POST_SIZE_PERCENTILE))

        topics = []

        for post in sorted(id_to_post.values(), key = lambda post: (post.length, len(post.text)), reverse = True):

            if post.id in ids and post.size >= min_post_length:

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

                ids.remove(post.id)

            if len(ids) < 1:
                break

        return topics
        # print(len(ids))
