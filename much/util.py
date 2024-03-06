import os
import re
from math import floor
from pathlib import Path

from requests import get

TIMEOUT = 3600

SPACE_TEMPLATE = re.compile(r'\s+')
PURE_SPACES_TEMPLATE = re.compile(r'\s*')
SPACE = ' '

DELETED_TRAILERS = ('"', "'", '`')

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')
VIDEO_EXTENSIONS = ('.mp4', '.webm')

ALLOWED_EXTENSIONS = (*IMAGE_EXTENSIONS, *VIDEO_EXTENSIONS)


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


def pull_original_poster(thread: dict, root: str, allowed_extensions = ALLOWED_EXTENSIONS):
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


def post_process_summary(text: str, min_duplicate_fraction: float = 0.25):
    input_text = text
    min_match_size = floor(len(text) * min_duplicate_fraction)

    # 1. Delete undesired headers / trailers

    for trailer in DELETED_TRAILERS:
        if text.startswith(trailer):
            text = text[1:]

        if text.endswith(trailer):
            text = text[:-1]

    # 2. Delete repeating chunks of text

    i = 0
    j = 0

    length = len(text)

    i_matches = []
    j_matches = []

    for i in range(length):
        for j in range(length):
            if i != j and text[i] == text[j]:
                i_ = i + 1
                j_ = j + 1

                while i_ < length and j_ < length and text[i_] == text[j_]:
                    i_ += 1
                    j_ += 1

                if j_ - j >= min_match_size:
                    i_match = (i, i_)
                    j_match = (j, j_)

                    if i_match not in j_matches:
                        for match in i_matches:
                            if match[0] <= i_match[0] and i_match[1] <= match[1]:
                                break
                        else:
                            for match in j_matches:
                                if match[0] <= i_match[0] and i_match[1] <= match[1]:
                                    break
                            else:
                                i_matches.append(i_match)
                                j_matches.append(j_match)

    if len(j_matches) > 0:
        longest_match = sorted(j_matches, key = lambda item: item[1] - item[0], reverse = True)[0]

        text = text[:longest_match[0]] + text[longest_match[1] + 1:]

    if input_text == text:
        return text.strip()

    return post_process_summary(text.strip(), min_duplicate_fraction = min_duplicate_fraction)


def is_image(path: str):
    return Path(path).suffix in IMAGE_EXTENSIONS


def is_video(path: str):
    return Path(path).suffix in VIDEO_EXTENSIONS
