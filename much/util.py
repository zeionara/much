import os
import re
from math import floor
from pathlib import Path

from requests import get, post as requests_post

TIMEOUT = 3600

SPACE_TEMPLATE = re.compile(r'\s+')
PURE_SPACES_TEMPLATE = re.compile(r'\s*')
SPACE = ' '
ALPHANUM_CHARACTER_TEMPLATE = re.compile(r'[a-zA-Z0-9\s]')

DELETED_TRAILERS = ('"', "'", '`')

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')
VIDEO_EXTENSIONS = ('.mp4', '.webm')

ALLOWED_EXTENSIONS = (*IMAGE_EXTENSIONS, *VIDEO_EXTENSIONS)

CAPTCHA_ERROR_CODE = 14


def post(url: str, data: dict, timeout: int = None, interactive: bool = True):
    def get_response(captcha_key: str = None, captcha_sid: str = None):
        if captcha_key is not None and captcha_sid is not None:
            data_ = dict(data)

            data_['captcha_key'] = captcha_key
            data_['captcha_sid'] = captcha_sid
        else:
            data_ = data

        return requests_post(url, data = data_, timeout = timeout)

    response = get_response()

    if response.status_code == 200 and interactive:
        response_json = response.json()

        if (error := response_json.get('error')) is not None and error.get('error_code') == CAPTCHA_ERROR_CODE:
            print(f'Captcha needed: {error.get("captcha_img")}')
            captcha_key = input('> ')

            response = get_response(captcha_key, error.get('captcha_sid'))

    return response


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
    # moved to raconteur module: https://github.com/zeionara/raconteur

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
            if i != j and text[i].lower() == text[j].lower():
                i_ = i + 1
                j_ = j + 1

                while i_ < length and j_ < length and text[i_].lower() == text[j_].lower():
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


def truncate_translation(text: str):
    # moved to raconteur module: https://github.com/zeionara/raconteur

    truncated_text = []

    for char in normalize(text.lower()).strip():
        if ALPHANUM_CHARACTER_TEMPLATE.fullmatch(char):
            truncated_text.append(char)

    return '-'.join(''.join(truncated_text).split(' '))


def is_image(path: str):
    # moved to raconteur module: https://github.com/zeionara/raconteur

    return Path(path).suffix in IMAGE_EXTENSIONS


def is_video(path: str):
    # moved to raconteur module: https://github.com/zeionara/raconteur

    return Path(path).suffix in VIDEO_EXTENSIONS
