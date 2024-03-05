import os
import re
from pathlib import Path

from requests import get

TIMEOUT = 3600

SPACE_TEMPLATE = re.compile('\s+')
PURE_SPACES_TEMPLATE = re.compile('\s*')
SPACE = ' '


def normalize(string: str):
    return SPACE_TEMPLATE.sub(SPACE, string).strip()


def pure_spaces(string: str):
    return PURE_SPACES_TEMPLATE.fullmatch(string) is not None


def make_ordinal(i: int):
    last_digit = i % 10

    if i < 10 or i > 20:
        if last_digit == 1:
            return f'{i}st'
        if last_digit == 2:
            return f'{i}nd'
        if last_digit == 3:
            return f'{i}rd'

    return f'{i}th'


def pull_original_poster(thread: dict, root: str, allowed_extensions = ('.png', '.jpg', '.jpeg')):
    thread_id = thread['num']

    print('handling thread', thread_id)

    for file in thread['files']:
        path = Path(file['path'])

        if (suffix := path.suffix) in allowed_extensions:
            link = f'https://2ch.hk{path}'
            local_path = os.path.join(root, f'{thread_id}{suffix}')

            if not os.path.isfile(local_path):
                try:
                    image = get(link, timeout = TIMEOUT).content
                except:
                    return

                print('+', local_path)

                with open(local_path, 'wb') as file:
                    file.write(image)

                return
        else:
            print('-', path)


def find_original_poster(thread: str, root: str):
    for file in os.listdir(root):
        if Path(file).stem == thread:
            return os.path.join(root, file)

    return None


def drop_original_poster(thread: str, root: str):
    for file in os.listdir(root):
        if Path(file).stem == thread:
            os.remove(removed_path := os.path.join(root, file))
            return removed_path

    return None
