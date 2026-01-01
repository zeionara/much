import re
import os
# from io import BytesIO, BufferedReader
from os import environ as env
from pathlib import Path
from shutil import copyfile, move
from html import unescape
from multiprocessing import Pool, Lock
from datetime import datetime, timedelta
from math import ceil  # , floor
from time import sleep
# from random import sample
import warnings
import pickle

warnings.filterwarnings('ignore', category = UserWarning)

from click import group, argument, option, Choice
from requests import get, post as postt
from bs4 import BeautifulSoup
from pandas import DataFrame, read_csv, concat
from tqdm import tqdm
from requests.exceptions import ConnectionError, ChunkedEncodingError
from flask import Flask
from karma import CloudMail
from torch.cuda import OutOfMemoryError

from rr import HuggingFaceClient, Task, post_process_summary, truncate_translation
from rr.alternator import _alternate

from .Fetcher import Fetcher, Topic, SSL_ERROR_DELAY
from .Exporter import Exporter, Format
from .Post import Post
from .util import normalize, SPACE, pull_original_poster, pull_original_posters, \
    drop_original_poster, find_original_poster, get_file_modification_datetime, find_file  # , post_process_summary, truncate_translation
# from .vk import upload_audio
from .ImageSearchEngine import ImageSearchEngine
from .nlp import summarize
from .VkClient import VkClient
# from .VkFileUploader import VkFileUploader
from .VkAudioUploader import VkAudioUploader
# from .VkPhotoUploader import VkPhotoUploader
# from .VkVideoUploader import VkVideoUploader
from .ArtistSampler import ArtistSampler
# from .folder import cached_folder
from .CloudFile import CloudFile
from .IndexEntry import IndexEntry


@group()
def main():
    pass


PATH = 'threads'
INDEX = 'index.tsv'

THREAD_URL = 'https://2ch.su/b/res/{thread}.html'
# ARHIVACH_THREAD_URL = '{protocol}://arhivach.top/thread/{thread}'
# ARHIVACH_INDEX_URL = '{protocol}://arhivach.top/index/{offset}'
ARHIVACH_THREAD_URL = '{protocol}://localhost:8080/thread/{thread}'
ARHIVACH_INDEX_URL = '{protocol}://localhost:8080/index/{offset}'
ARHIVACH_CACHE_PATH = 'assets/cache.html'

BOARD_NAME_TEMLATE = re.compile('/[a-zA-Z0-9]+/')
TIME_TEMPLATE = re.compile('[0-9]+:[0-9]+')
NEWLINE = '\n'

VK_API_VERSION = '5.199'

POSTERS_DEFAULT_ROOT = '/tmp/much-images'
MIN_SUMMARY_LENGTH = 40

empty_list_lock = Lock()


def _get_board_name(thread: BeautifulSoup):
    for link in (tags := thread.find('div', {'class': 'thread_tags'})).find_all('a'):
        boards = BOARD_NAME_TEMLATE.findall(link['title'])

        if len(boards) > 0:
            return boards[0]

    # raise ValueError("Can't infer board: ", tags)

    print("Can't infer board: ", tags)

    return None


def _decode_date(date: str):
    normalized = normalize(date).lower()

    if normalized.startswith('сегодн'):
        return datetime.today().strftime('%d-%m-%Y')
    elif normalized.startswith('вчера'):
        return (datetime.today() - timedelta(days = 1)).strftime('%d-%m-%Y')

    try:
        day, month, year = normalized.split(SPACE)
    except ValueError:
        print(f'Can\'t decode date: {date}')
        return date

    match month:
        case 'января':
            decoded_month = 1
        case 'февраля':
            decoded_month = 2
        case 'марта':
            decoded_month = 3
        case 'апреля':
            decoded_month = 4
        case 'мая':
            decoded_month = 5
        case 'июня':
            decoded_month = 6
        case 'июля':
            decoded_month = 7
        case 'августа':
            decoded_month = 8
        case 'сентября':
            decoded_month = 9
        case 'октября':
            decoded_month = 10
        case 'ноября':
            decoded_month = 11
        case 'декабря':
            decoded_month = 12
        case _:
            raise ValueError(f"Can't infer month from date: {date}")

    try:
        return f'{int(day):02d}-{decoded_month:02d}-{int(year):04d}'
    except ValueError:
        if TIME_TEMPLATE.fullmatch(year):
            return f'{int(day):02d}-{decoded_month:02d}-{datetime.now().year:04d}'

        print(f'Can\'t decode date: {date}')
        return date


def make_grabbed_folder_path(i: int, batch_size: int, path: str = None):
    offset = i // batch_size * batch_size
    batch_max_count = offset + batch_size - 1
    batch_folder_name = BATCH_FOLDER_NAME.format(first = offset, last = batch_max_count)

    if path is None:
        return batch_folder_name

    return os.path.join(path, batch_folder_name)


TIMEOUT = 3600


@main.command()
@option('--index', '-i', type = str, default = INDEX)
@option('--path', '-p', type = str, default = PATH)
@option('--mtime-path', '-m', type = str, default = PATH)
def create_missing_index_entries(index: str, path: str, mtime_path: str):
    index = read_csv(index, sep = '\t')

    indexed_threads = set()
    entries = []

    for _, row in tqdm(tuple(index.iterrows()), desc = 'Reading index'):
        entry = IndexEntry.from_json(row.to_dict())

        entries.append(entry)
        indexed_threads.add(entry.thread_id)

    n_matched_entries = 0
    n_missing_index_entries = 0

    for file in tqdm(os.listdir(path), desc = 'Handling threads'):
        if not file.endswith('txt'):
            continue

        thread_id = int(file.split('.')[0])

        if thread_id in indexed_threads:
            n_matched_entries += 1
        else:
            n_missing_index_entries += 1

            if path == mtime_path:
                timestamp = get_file_modification_datetime(os.path.join(path, file))
            else:
                files = find_file(file, mtime_path)

                if len(files) < 1:
                    raise ValueError(f'Can\'t find file {file} in {mtime_path}')

                if len(files) > 1:
                    print(f'Found miltiple files with name {file} in {mtime_path}:')

                    for file in files:
                        print(f'{file}: {get_file_modification_datetime(file)}')

                    print('Taking the last one')

                    # raise ValueError(f'Found multiple files with name {file} in {mtime_path}')

                timestamp = get_file_modification_datetime(files[-1])

            with open(os.path.join(path, file), 'r') as f:
                title = f.readline().strip()

            entries.append(
                IndexEntry(
                    thread_id = thread_id,
                    timestamp = timestamp,
                    title = title
                )
            )

    with open('assets/index.pkl', 'wb') as file:
        pickle.dump(entries, file)

    response = input(f'Found {n_matched_entries} matched entries and {n_missing_index_entries} missing entries in the index, total number of entries will be {len(entries)}. Insert missing? [Y/n]: ')

    if response != 'Y':
        print('Cancelling the operation')


@main.command()
def sample_artist():
    sampler = ArtistSampler()

    print(sampler.artists)

    print(sampler.sample())


# @option('--max-length', '-m', type = int, default = 10)
# def summarize_(path: str, max_length: int, verbose: bool, model: str):
@main.command(name = 'summarize')
@argument('path', type = str)
@option('--verbose', '-v', is_flag = True)
@option('--model', '-m', type = str, default = 'IlyaGusev/rut5_base_headline_gen_telegram')
@option('--min-duplicate-fraction', '-f', type = float, default = 0.25)
@option('--local', '-l', is_flag = True)
def summarize_(path: str, verbose: bool, model: str, min_duplicate_fraction: float, local: bool):
    # print("'" + post_process_summary('"`Не удалёнщики, а каноничные двачеры? Есть тут хикки 30+ лвла? Не удалёнщики, а каноничные двачеры?"') + "'")
    # print("'" + post_process_summary('foo bar baz qux quux quuz bar baz qux quux') + "'")

    summarization_client = HuggingFaceClient(model = model, local = local, hf_cache = 'hf-cache', device = 0)
    translation_client = HuggingFaceClient(model = 'Helsinki-NLP/opus-mt-ru-en', task = Task.TRANSLATION, local = local, hf_cache = 'hf-cache', device = 0)

    sources = [
        """
        Напоминаю ей, что сейчас любую лишнюю копейку надо направлять на утилизацию чубатой скотины, поэтому не только я эту тысячу отправлю героям СВО, но и им бы надо сделать то же самое.
        """, """
        Сап двач, почему ты такой токсичный? Все из вас, пока не тут, порядочные люди. Не оскорбляют и в рот не кому не оформляют.
        Но почему стоит вам открыть эту помойку, как сразу вы превращаетесь в животных натурально. Почему так? я такой же
        """,
        """
        СПАЛИЛА СЕСТРА ЗА ДРОЧКОЙ ТРЕД Анон, это просто пиздец.... Сейчас сидел в зале на стуле на корячкях и люто дрочил на порно с телефона.
        И тут в зал входит старшая сестра ей 25 , бляяя это пиздец.... Думаю что увидела мой хуй т что я дрочу, но виду не подола просто спросила когда пойду спать,
        но в её голосе какая-то хуйня странная была. Руки у меня сейчас дрожать что пиздец стали. Но я всё таки подрочил и слил на ковёр. Блят сука я на колясках как далбоеб сидел с голой
        жопой и хуем. Это пизда, анон, никогда не забуду.... Подскажите что мне делать то блять? У тебя были случаи когда тебя спаливала за фапом мамка или сестра?
        Дополнение: после этого сестра пошла в ванну, сейчас купается, но не думаю что она фапает, скорее в ахуи если увидела
        """
    ]

    summaries = [post_process_summary(summary) for summary in summarization_client.infer_many(sources)]
    translations = [truncate_translation(translation) for translation in translation_client.infer_many(summaries)]

    print(summaries)
    print(translations)
    print(summarization_client.apply(sources[0]))

    # for _ in range(10):
    #     print(
    #         post_process_summary(
    #             HuggingFaceClient(model = model, local = local, hf_cache = 'hf-cache', device = 0).summarize(path, verbose),
    #             min_duplicate_fraction = min_duplicate_fraction
    #         )
    #     )

    # print(summarize(path, max_length = max_length))


@main.command()
@argument('query', type = str)
def search(query: str):
    for url in ImageSearchEngine().search(query):
        print(url)


class Foo:
    def __init__(self):
        self.foo = 'foo'
        self.i = 1

    # @retry(times = 3)
    def wait_and_rise(self):
        print('waiting')

        sleep(2)

        if self.i > 1:
            return self.foo

        self.i += 1
        raise ValueError('foo')


@main.command()
@argument('path', type = str)
@option('--verbose', '-v', is_flag = True)
def upload_file(path: str, verbose: bool):
    # uploader = VkFileUploader.make()
    # uploader.upload(path, title = 'Foo bar', tags = ['qux', 'quux'])

    # VkAudioUploader.make().upload(path, title = 'Blah blah', artist = 'Foo bar')
    # print(Foo().wait_and_rise())

    # photo_id = VkPhotoUploader.make().upload(path, 'Foo bar baz', verbose = True)
    # video_id = VkVideoUploader.make().upload(path, 'Foo bar baz', 'qux quux quuz', verbose = True)

    audio_id = VkAudioUploader.make().upload('foo.mp3', 'foo', 'foo', verbose)
    print(audio_id)

    # print(photo_id)
    # print(video_id)


@main.command()
@argument('name', type = str)
@option('--artist', '-a', type = str, default = 'None')
@option('--root', '-r', type = str, default = 'audible')
@option('--verbose', '-v', is_flag = True)
@option('--poster', '-p', type = str)
def post(name: str, artist: str, root: str, verbose: bool, poster: str):
    name_with_suffix = name   # f'{name}-full'
    caption = name.replace('-', ' ').strip().capitalize()

    post_id = VkClient().post(
        os.path.join(root, f'{name_with_suffix}.mp3'),
        summarize(
            os.path.join(root, f'{name_with_suffix}.txt'),
            default = caption,
            max_length = 7
        ),
        caption,
        artist,
        poster = poster,
        verbose = verbose
    )

    print(f'Posted as {post_id}')


@main.command()
@option('--root', '-r', default = '/2ch')
@option('--username', '-u', type = str)
@option('--password', '-p', type = str)
@option('--batch-size', '-b', type = int, default = 100)
@option('--cookies', '-c', type = str, default = 'cloud-mail-cookies.json')
def cleanup(root: str, username: str, password: str, batch_size: int, cookies: str):
    # if os.path.isfile(cookies):
    #     cm = CloudMail(None, None)
    #     cm.load_cookies_from_file(cookies)
    # else:
    if username is None:
        username = env.get('KARMA_USERNAME')

        if username is None:
            raise ValueError('Cloud mail ru username is required')

    if password is None:
        password = env.get('KARMA_PASSWORD')

        if password is None:
            raise ValueError('Cloud mail ru password is required')

    cm = CloudMail(username, password)
    cm.auth()

    # cm.save_cookies_to_file(cookies)

    files = []

    offset = 0

    with tqdm() as pbar:
        while True:
            folder = cm.api.folder(root, limit = batch_size, offset = offset, sort = {'type': 'date', 'order': 'desc'})

            # folder = cached_folder

            body = folder['body']

            if pbar.total is None:
                count = body['count']

                n_folders = count['folders']
                n_files = count['files']

                pbar.total = n_folders + n_files
                pbar.refresh()

            n_total = 0

            for file in body['list']:
                if file['kind'] == 'file':
                    files.append(CloudFile.from_json(file))

                n_total += 1

            pbar.update(n_total)

            # print(body['list'][0]['name'], offset, n_total)

            if n_total < batch_size:
                break

            offset += n_total

    filenames = [file.name for file in sorted(files, key = lambda file: file.timestamp, reverse = True)]
    filenames_for_deletion = []

    for name in filenames:
        path = Path(name)

        stem = path.stem
        suffix = path.suffix

        if (snapshot_name := f'{stem}-snapshot{suffix}') in filenames:
            filenames_for_deletion.append(snapshot_name)

    # print(filenames_for_deletion, len(filenames_for_deletion))

    for filename in tqdm(filenames_for_deletion):
        cm.api.file.remove(f'{root}/{filename}')

    print(f'Deleted {len(filenames_for_deletion)} files')


@main.command()
@argument('path', default = 'alternation-list.txt')
@argument('threads', default = 'threads')
@argument('alternated', default = 'audible')
@option('--artist-one', '-a1', help = 'first artist to say the replic', default = 'xenia')
@option('--artist-two', '-a2', help = 'second artist to say the replic', default = 'baya')
@option('--poster-root', '-r', type = str, default = POSTERS_DEFAULT_ROOT)
@option('--verbose', '-v', is_flag = True)
@option('--force', '-f', is_flag = True)
@option('--interactive', '-i', is_flag = True)
def alternate(path: str, threads: str, alternated: str, artist_one: str, artist_two: str, poster_root: str, verbose: bool, force: bool, interactive: bool):
    input_entries = []
    output_entries = []

    # token = env.get('MUCH_VK_TOKEN')

    # if token is None:
    #     raise ValueError('vk token is required to post content')

    # token_owner = env.get('MUCH_VK_USER_ID')

    # if token_owner is None:
    #     raise ValueError('vk user id is required to post content')

    # audio_owner = env.get('MUCH_VK_GROUP_ID')

    # if audio_owner is not None:
    #     audio_owner = int(audio_owner)

    # if not os.path.isfile(path):
    #     raise ValueError(f'No such file: {path}')

    # 1. Read the file

    with open(path, 'r', encoding = 'utf-8') as file:
        for line in file.readlines():
            thread, name = line[:-1].split(' ', maxsplit = 1)
            input_entries.append({'thread': thread, 'name': name})

    # 2. Check which threads are no longer available, and alternate them

    vk_client = VkClient(interactive = interactive)
    # file_uploader = VkFileUploader.make()

    hf_client = HuggingFaceClient(hf_cache = 'hf-cache', local = True, device = 0)
    artist_sampler = ArtistSampler()

    for entry in input_entries:
        thread = entry['thread']
        name = entry['name']

        response = get(THREAD_URL.format(thread = thread), timeout = TIMEOUT)

        if response.status_code == 404:
            target_txt_path = os.path.join(alternated, f'{name}.txt')
            target_mp3_path = os.path.join(alternated, f'{name}.mp3')

            print(f'Alternating thread {thread} as {target_txt_path}...')
            found_thread = False

            if not os.path.isfile(target_txt_path):
                for batch_path in os.listdir(threads):
                    # print(batch_path)
                    for file in os.listdir(batch_full_path := os.path.join(threads, batch_path)):
                        # print(file, thread)
                        if file.startswith(thread):
                            copyfile(os.path.join(batch_full_path, file), target_txt_path)
                            found_thread = True
                            break
                    if found_thread:
                        break

                if not found_thread:
                    print(f'Can\'t find thread {thread}. Skipping...')
                    continue

            with open(target_txt_path, 'r', encoding = 'utf-8') as file:
                first_post = file.readline()[:-1]

            if not os.path.isfile(target_mp3_path) or force:
                if not os.path.isfile(target_mp3_path):
                    _alternate(target_txt_path, artist_one, artist_two)

                # artist = sample(['Анон', 'Анонимус', 'Чел', 'Пчел', 'Челик', 'Ананас', 'Анончик', 'Anonymous', 'Unknown', 'Unnamed', 'Incognito', 'Hidden', 'None', 'Nil', 'Null', 'Антон'], k = 1)[0]
                # artist = artist_sampler.sample()

                # caption = name.replace('-full', '').replace('-', ' ').strip().capitalize()
                caption = name.replace('-', ' ').strip().capitalize()

                # upload_audio(target_mp3_path, caption, artist, token, token_owner, audio_owner, api_version = VK_API_VERSION)

                try:
                    summary = first_post if len(first_post) <= MIN_SUMMARY_LENGTH else post_process_summary(hf_client.apply(first_post))
                except (ValueError, OutOfMemoryError):
                    summary = summarize(target_txt_path, max_length = 7, default = caption)

                # post_id = vk_client.post2(
                vk_client.post2(
                    audio_path = target_mp3_path,
                    poster_path = find_original_poster(thread, poster_root),
                    file_path = target_txt_path,

                    caption = summary,
                    description = first_post,
                    artist = artist_sampler.sample(),
                    file_tags = ['2ch', 'anon', 'thread'],
                    verbose = verbose
                )

                # print(post_id)

                # file = file_uploader.upload(target_txt_path, summary, tags = ['2ch', 'anon', 'thread'])

                # vk_client.post(
                #     path = target_mp3_path,
                #     title = summary,
                #     caption = caption,
                #     artist = artist_sampler.sample(),
                #     message = first_post,
                #     poster = find_original_poster(thread, poster_root),
                #     file = file,
                #     verbose = verbose
                # )
        else:
            output_entries.append(entry)

    # 3. Write the file

    with open(path, 'w', encoding = 'utf-8') as file:
        file.writelines([f'{entry["thread"]} {entry["name"]}{NEWLINE}' for entry in output_entries])


@main.command()
@option('--threads', '-t', help = 'Path to the root folder with threads', default = 'threads')
def list_empty_threads(threads: str):
    batch_paths = os.listdir(threads)

    n_threads = 0
    n_empty_threads = 0

    for batch_path in tqdm(batch_paths):
        for thread in os.listdir(batch_full_path := os.path.join(threads, batch_path)):
            file_stat = os.stat(os.path.join(batch_full_path, thread))

            if file_stat.st_size < 1:
                n_empty_threads += 1

            n_threads += 1

    print(f'{n_empty_threads} / {n_threads} threads are empty ({100 * n_empty_threads / n_threads:.3f}%)')


@main.command()
@option('--source', '-s', default = 'index.tsv')
@option('--destination', '-d', default = 'index.tsv')
@option('--batch-size', '-b', help = 'How many threads to put in a folder', default = 10000)
@option('--threads', '-t', help = 'Path to the root folder with threads', default = 'threads')
@option('--pretend', '-p', is_flag = True)
def sort(source: str, destination: str, batch_size: int, threads: str, pretend: bool):
    df = read_csv(source, sep = '\t')

    if 'folder' not in df.columns:
        df['folder'] = df.index.to_series().apply(lambda i: make_grabbed_folder_path(i, batch_size, threads))
    else:
        thread_id_to_folder = {}

        for root, dirs, files in os.walk(threads):
            for name in files:
                thread_id_to_folder[int(name.split('.')[0])] = root

        # df['folder'] = df.apply(lambda cell: detect_folder(threads, cell['thread']) if isinstance(cell.get('folder'), float) else os.path.join(threads, cell['folder']))
        df['folder'] = df.apply(lambda cell: os.path.join(threads, cell['folder']) if isinstance(cell['folder'], str) else thread_id_to_folder[cell['thread']], axis = 1)

    df.sort_values(by = ['thread'], inplace = True)

    for i, row in df.iterrows():
        folder_after_sorting = make_grabbed_folder_path(i, batch_size, threads)
        folder_before_sorting = row['folder']
        thread = row['thread']

        thread_path_before_sorting = os.path.join(folder_before_sorting, f'{thread:08d}.txt')
        thread_path_after_sorting = os.path.join(folder_after_sorting, f'{thread:08d}.txt')

        # if os.path.isfile(thread_path_before_sorting):
        #     print(thread_path_before_sorting)

        if folder_after_sorting != folder_before_sorting:  # and os.path.isfile(thread_path_before_sorting):
            print(thread_path_before_sorting, '->', thread_path_after_sorting)
            if not pretend:
                move(thread_path_before_sorting, thread_path_after_sorting)

    if not pretend:
        df['folder'] = df.index.to_series().apply(lambda i: make_grabbed_folder_path(i, batch_size))
        df.to_csv(destination, sep = '\t', index = False)


@main.command()
# @argument('url', type = str, default = 'http://arhivach.top/index/{offset}/')
@argument('url', type = str, default = ARHIVACH_INDEX_URL)
@option('--start', '-s', type = int, default = 935475)
@option('--debug', '-d', is_flag = True)
@option('--n-top', '-n', type = int, default = None)
@option('--index', '-i', type = str, default = None)
@option('--step', '-t', type = int, default = 25)
@option('--protocol', '-r', type = Choice(('http', 'https'), case_sensitive = True), default = 'http')
def filter(url: str, start: int, debug: bool, n_top: int, index: str, step: int, protocol: str):
    records = []

    if index is None:
        content = None
        seen_keys = set()
    else:
        content = read_csv(index, sep = '\t')
        seen_keys = set(content.thread)

        if len(seen_keys) != content.shape[0]:
            raise ValueError(f'Input index contains duplicates ({len(seen_keys)} != {content.shape[0]})')

    if index is None:
        index = 'index.tsv'

    def handle_page(page: str):
        bs = BeautifulSoup(page, 'html.parser')

        for thread in bs.find_all('tr')[1:][::-1]:
            _text = thread.find('div', {'class': 'thread_text'})
            key = int(_text.find('a')['href'].split('/')[2])

            if key in seen_keys:
                # print(f'skipping thread {key} which has already been handled')
                continue

            seen_keys.add(key)

            text = normalize(_text.get_text(separator = SPACE))
            n_stars = int(thread.find('span', {'class': 'thread_posts_count'}).text)

            date = _decode_date(thread.find('td', {'class': 'thread_date'}).text)

            board = _get_board_name(thread)

            records.append({
                'thread': key,
                'title': text,
                'date': date,
                'board': board,
                'stars': n_stars
            })

        # print(text, n_stars, board, key, date)

    def save():
        df = DataFrame.from_records(records)
        if content is None:
            df.to_csv(index, sep = '\t', index = False)
        else:
            concat([content, df]).to_csv(index, sep = '\t', index = False)

    if os.path.isfile(ARHIVACH_CACHE_PATH) and debug:
        with open(ARHIVACH_CACHE_PATH, encoding = 'utf-8', mode = 'r') as file:
            page = file.read()
        handle_page(page)

        save()
    else:
        i = 0
        offset = start

        pbar = tqdm(total = ceil(start / step) if n_top is None else n_top)

        while (n_top is None or i < n_top) and (offset >= 0):
            response = None

            while response is None or response.status_code != 200 or (len(response.text) < 1):
                # try:

                # print(response)

                try:
                    response = get(url.format(protocol = protocol, offset = offset), timeout = TIMEOUT)
                except (ConnectionError, ChunkedEncodingError) as e:
                    print(f'Encountered error when fetching page wit offset {offset}: {e}. Waiting for {SSL_ERROR_DELAY} before retrying...')
                    sleep(SSL_ERROR_DELAY)
                    print('Retrying...')
                    response = None
                # code = response.status_code

                # if (code := response.status_code) != 200:
                #     raise ValueError(f'Inacceptable status code: {code}')

            handle_page(response.text)

            if i % 100 == 0:
                save()

            i += 1
            offset -= step
            pbar.update()

            # if debug:
            #     with open(ARHIVACH_CACHE_PATH, encoding = 'utf-8', mode = 'w') as file:
            #         file.write(page)

        save()

        print('To continue, run command:')
        print(f'python -m much filter -t {step} -i {index} -n {n_top} -s {offset + step}')


@main.command()
@argument('url', type = str, default = 'https://2ch.hk/b/catalog.json')
@option('--root', '-r', help = 'folder, in which pulled images will be stored', default = POSTERS_DEFAULT_ROOT)
def pull_images(url: str, root: str):
    if not os.path.isdir(root):
        os.makedirs(root)

    response = get(url)

    if (code := response.status_code) != 200:
        raise ValueError(f'Unexpected status code: {code}')

    json = response.json()

    for thread in json['threads'][:10]:
        pull_original_poster(thread, root)


@main.command()
@argument('thread', type = str)
@option('--root', '-r', help = 'folder, in which pulled images are stored', default = POSTERS_DEFAULT_ROOT)
def drop_image(thread: str, root: str):
    removed_path = drop_original_poster(thread, root)

    if removed_path is None:
        print('No matching file')
    else:
        print(f'Removed file {removed_path}')


@main.command()
@argument('url', type = str, default = 'https://2ch.su/b/catalog.json')
@option('--path', '-p', type = str, default = 'threads')
@option('--index', '-i', type = str, default = 'index.tsv')
@option('--batch-size', '-b', help = 'how many threads to put in a folder', default = 10000)
@option('--top-n', '-n', type = int, help = 'handle only first n entries', default = None)
@option('--poster-root', '-r', type = str, default = POSTERS_DEFAULT_ROOT)
def load(url: str, path: str, index: str, batch_size: int, top_n: int, poster_root: str):
    last_records_list = read_csv(index, sep = '\t').to_dict(orient = 'records') if os.path.isfile(index) else None
    last_records = None if last_records_list is None else {
        item['thread']: item
        for item in last_records_list
    }

    if not os.path.isdir(poster_root):
        os.makedirs(poster_root)

    if not os.path.exists(path):
        os.makedirs(path)

    response = get(url)

    if (code := response.status_code) != 200:
        raise ValueError(f'Inacceptable status code: {code}')

    json = response.json()
    records_list = []
    records = {}

    offset = 1
    batch_max_count = offset + batch_size - 1

    batch_folder_size = None
    batch_folder_name = None
    batch_folder_path = None

    def refresh_batch_folder_path():
        nonlocal offset, batch_max_count, batch_folder_size, batch_folder_name, batch_folder_path

        while True:
            batch_folder_name = BATCH_FOLDER_NAME.format(first = offset, last = batch_max_count)
            batch_folder_path = os.path.join(path, batch_folder_name)
            batch_folder_size = None

            if os.path.isdir(batch_folder_path):
                batch_folder_size = len(os.listdir(batch_folder_path))

                if batch_folder_size < batch_size:  # Found an existing folder which is not full
                    break

                offset = batch_max_count + 1
                batch_max_count = offset + batch_size - 1
            else:
                os.makedirs(batch_folder_path)
                batch_folder_size = 0

    refresh_batch_folder_path()

    fetcher = Fetcher()
    exporter = Exporter()

    for thread in tqdm(json['threads'] if top_n is None else json['threads'][:top_n]):
        day, month, year = thread['date'].split(' ')[0].split('/')

        thread_id = thread['num']

        pull_original_posters(thread, poster_root)

        last_thread_path = None
        last_batch_folder_name = None

        if last_records is not None and (last_record := last_records.get(thread_id)) is not None:  # If thread has already been associated with a folder
            try:
                last_thread_path = os.path.join(path, last_record['folder'], f'{thread_id}.txt')
            except TypeError:
                pass
            last_batch_folder_name = last_record['folder']

        if last_thread_path is None and batch_folder_size >= batch_size:  # If thread has not been associated with a folder, and number of files in current folder reached maximum, then create new
            refresh_batch_folder_path()

        topics = fetcher.fetch(THREAD_URL.format(thread = thread_id))
        is_empty = len(topics) < 1

        records_list.append(
            record := {
                'thread': thread_id,
                'date': f'{day}-{month}-20{year}',
                'title': Post.from_body(BeautifulSoup(thread['comment'], 'html.parser'))[1].text,
                'folder': None if is_empty else batch_folder_name if last_batch_folder_name is None else last_batch_folder_name,
                'open': True
            }
        )

        if is_empty:
            print(f'Empty thread {thread_id}')
            continue

        exporter.export(
            topics,
            format = Format.TXT,
            path = (os.path.join(batch_folder_path, f'{thread_id}.txt') if last_thread_path is None else last_thread_path)
        )

        records[thread_id] = record

        if last_thread_path is None:
            batch_folder_size += 1

    if last_records is None:
        df = DataFrame.from_records(records_list)
    else:
        for thread, item in last_records.items():
            if thread not in records and item['open'] is True:
                item['open'] = False

        for thread, item in records.items():
            if thread not in last_records:
                last_records_list.append(item)

        df = DataFrame(last_records_list)

    df.to_csv(index, sep = '\t', index = False)


@main.command()
@argument('url', type = str)
@argument('path', type = str)
def pull(url: str, path: str):
    topics = Fetcher().fetch(url)

    exporter = Exporter()

    if path.endswith(Format.JSON.value):
        exporter.export(topics, Format.JSON, path)
    elif path.endswith(Format.TXT.value):
        exporter.export(topics, Format.TXT, path)
    else:
        raise ValueError(f'Incorrect output file extension: {path}. Can\'t infer output file format')

    # for topic in topics:
    #     print(topic.title)
    #     for comment in topic.comments:
    #         print(comment)
    #     print()


ROOT = 'https://2ch.hk'
PAGE_TEMPLATE = f'{ROOT}/b/arch/{{id}}.html'

# PATH = '../batch/batch'
# INDEX = '../batch/index.tsv'




def expand_title(title: str, topics: [Topic]):
    title = unescape(title)

    for topic in topics:
        match = topic.find(title)

        if match is not None:
            return match

    return title


BATCH_FOLDER_NAME = '{first:08d}-{last:08d}'


def grab_one(i: int, row: dict, batch_size: int, path: str, skip_empty: bool, protocol: str, empty_list_path: str, empty_threads: list[int]):
    fetcher = Fetcher()
    exporter = Exporter()

    thread = row['thread']

    # if i > batch_max_count:
    offset = i // batch_size * batch_size
    batch_max_count = offset + batch_size - 1
    batch_folder_name = BATCH_FOLDER_NAME.format(first = offset, last = batch_max_count)
    batch_folder_path = os.path.join(path, batch_folder_name)

    if not os.path.isdir(batch_folder_path):
        try:
            os.makedirs(batch_folder_path)
        except FileExistsError:
            pass

    thread_path = os.path.join(batch_folder_path, f'{thread:08d}.txt')

    # if pretend:
    # print(f'Saving {thread_path}...')
    # return
    # pbar.update()
    # continue

    url = ARHIVACH_THREAD_URL.format(thread = thread, protocol = protocol)

    if os.path.isfile(thread_path) and (skip_empty or thread in empty_threads or os.stat(thread_path).st_size > 0):
        # print(f'File {thread_path} exists. Not pulling')
        # pbar.update()
        return
        # continue

    fetched = False

    while not fetched:
        try:
            exporter.export(fetcher.fetch(url = url, verbose = False), Format.TXT, path = thread_path)

            if os.stat(thread_path).st_size < 1:
                with empty_list_lock:
                    with open(empty_list_path, mode = 'a', encoding = 'utf-8') as file:
                        file.write(f'{thread}\n')

            fetched = True
        except ConnectionError:
            continue

    # pbar.update()


@main.command()
@option('--path', '-p', type = str, help = 'path to the directory which will contain pulled files', default = 'threads')
@option('--index', '-i', type = str, help = 'path to the file with pulled files indes', default = 'index.tsv')
@option('--batch-size', '-b', type = int, help = 'how many threads to put in a folder', default = 10000)
@option('--verbose', '-v', is_flag = True)
@option('--pretend', '-e', is_flag = True)
@option('--n-workers', '-n', type = int, default = 8)
@option('--skip-empty', '-s', is_flag = True)
@option('--protocol', '-r', type = str, default = 'http')
@option('--empty-list-path', '-y', type = str, default = 'empty-threads.txt')
def grab(path: str, index: str, batch_size: int, verbose: bool, pretend: bool, n_workers: int, skip_empty: bool, protocol: str, empty_list_path: str):
    if not os.path.isdir(path):
        os.makedirs(path)

    df = read_csv(index, sep = '\t')

    if os.path.isfile(empty_list_path):
        with open(empty_list_path, 'r', encoding = 'utf-8') as file:
            empty_threads = [int(line[:-1]) for line in file.readlines() if len(line) > 0]
    else:
        empty_threads = tuple()

    # fetcher = Fetcher()
    # exporter = Exporter()

    # offset = 0
    # batch_max_count = offset + batch_size - 1
    # batch_folder_name = BATCH_FOLDER_NAME.format(first = offset, last = batch_max_count)
    # batch_folder_path = os.path.join(path, batch_folder_name)

    # if not os.path.isdir(batch_folder_path):
    #     os.makedirs(batch_folder_path)

    # pbar = tqdm(total = df.shape[0])

    # for i, row in df.iterrows():
    #     grab_one((i, row, batch_size, path))

    with Pool(processes = n_workers) as pool:
        # Use pool.starmap to parallelize the loop
        pool.starmap(grab_one, [(i, row, batch_size, path, skip_empty, protocol, empty_list_path, empty_threads) for i, row in df.iterrows()])


@main.command()
@argument('page', type = int)
@option('--path', '-p', type = str, help = 'path to the directory which will contain pulled files', default = PATH)
@option('--index', '-i', type = str, help = 'path to the file with pulled files index', default = INDEX)
@option('--skip-fetched', '-s', is_flag = True, help = 'skip posts, for which corresponding files already exist')
def fetch(page: int, path: str, index: str, skip_fetched: bool):
    if not os.path.isdir(path):
        os.makedirs(path)

    url = PAGE_TEMPLATE.format(id = page)
    # print(url)
    response = get(url)

    if (code := response.status_code) != 200:
        raise ValueError(f'Inacceptable response status: {code}')

    bs = BeautifulSoup(response.text, 'html.parser')

    i = 0

    records = []

    fetcher = Fetcher()
    exporter = Exporter()

    for thread in tqdm(bs.find_all('span', {'class': 'arch-threadnum'})):
        # records.append({'thread': int(thread.text[2:-2]), 'date': f'{ROOT}{link["href"]}', 'title': link.text})

        thread_id = int(thread.text[2:-2])
        file = os.path.join(path, f'{thread_id}.txt')

        if os.path.isfile(file) and skip_fetched:
            continue

        link = thread.find_previous("a")
        exporter.export(topics := fetcher.fetch(url = f'{ROOT}{link["href"]}'), Format.TXT, path = file)

        records.append({
            'thread': thread_id,
            'date': '-'.join(link["href"].split('/')[3].split('-')[::-1]),
            'path': path,
            'title': expand_title(title = link.text, topics = topics)
        })

        i += 1

    # print(f'Pulled {i} threads')
    # print(records[:5])

    if len(records) > 0:
        df = DataFrame.from_records(records)
        df = df[['thread', 'date', 'path', 'title']]  # reorder columns for convenience

        if os.path.isfile(index):
            df = concat([read_csv(index, sep = '\t'), df])

        df.to_csv(index, sep = '\t', index = False)


@main.command()
@argument('n', type = int, default = 10)
@option('--root', '-r', type = str, help = 'root folder with threads', default = None)
@option('--path', '-p', type = str, help = 'path to the directory which will contain pulled files', default = PATH)
@option('--index', '-i', type = str, help = 'path to the file with pulled files index', default = INDEX)
@option('--skip-missing', '-s', is_flag = True)
def top(n: int, path: str, index: str, root: str, skip_missing: bool):
    index = read_csv(index, sep = '\t')

    if root is not None:
        index['path'] = index['folder'].apply(lambda x: os.path.join(root, x))

    for folder, file in sorted(
        [
            (folder, os.path.join(folder, file))
            for folder, _, files in os.walk(path)
            for file in files
        ],
        key = lambda folder_and_file: os.stat(folder_and_file[1]).st_size,
        reverse = True
    )[:n]:
        thread_id = int(Path(file).stem)

        try:
            row = index.loc[(index.thread == thread_id) & (index.path == folder)].iloc[0]
        except IndexError:
            print(f"-- Can't find thread {thread_id} at {folder} in index")
            if skip_missing:
                continue
            else:
                raise

        print(
            f'{os.stat(file).st_size / 1024:.2f} KB',
            thread_id,
            row['title']
        )


@main.command()
@argument('thread-id', type = int)
@argument('name', type = str)
@option('--index', '-i', type = str, default = INDEX)
@option('--root', '-r', type = str, help = 'root folder with threads', default = None)
@option('--destination-path', '-d', type = str, help = 'path where the chosen file will be copied with given name', default = 'assets/starred')
def star(thread_id: int, name: str, index: str, root: str, destination_path: str):
    if not os.path.isdir(destination_path):
        os.mkdir(destination_path)

    index = read_csv(index, sep = '\t')

    row = index.loc[index.thread == thread_id].iloc[0]

    if root is None:
        thread_path = row['path']
    else:
        thread_path = os.path.join(root, row['folder'])

    copyfile(os.path.join(thread_path, f'{thread_id}.txt'), os.path.join(destination_path, f'{name}.txt'))


@main.command()
@argument('thread-id', type = int)
@option('--index', '-i', type = str, default = INDEX)
def link(thread_id: int, index: str):
    index = read_csv(index, sep = '\t')

    items = index[index.thread == thread_id]

    if (size := items.shape[0]) < 1:
        raise ValueError(f'Too few matching items: {size}')

    if (size := items.shape[0]) > 1:
        raise ValueError(f'Too many matching items: {size}')

    record = items.iloc[0].to_dict()

    print(f'https://2ch.hk/b/arch/{"-".join(record["date"].split("-")[::-1])}/res/{record["thread"]}.html')


@main.command()
@option('--index', '-i', type = str, default = INDEX)
@option('--path', '-p', type = str, default = PATH)
@option('--target', '-t', type = str, default = 'orphan')
def sync(index: str, path: str, target: str):
    index = read_csv(index, sep = '\t')

    if not os.path.isdir(target):
        os.makedirs(target)

    print('indexing...')

    pairs = set()
    for _, row in index.iterrows():
        pair = (row['thread'], row['folder'])

        if pair in pairs:
            raise ValueError(f'There are multiple threads with id {row["thread"]} in folder {row["folder"]}')

        pairs.add(pair)

    print('indexed')

    for path, _, files in os.walk(path):
        for file in files:
            folder = Path(path).stem
            thread_id = int(Path(file).stem)

            # row = index.loc[(index.thread == thread_id) & (index.folder == folder)]
            # size = row.shape[0]

            # if size > 1:
            #     raise ValueError(f'There are multiple threads with id {thread_id} in folder {folder}')

            if (thread_id, folder) not in pairs:
                print(f'Missing index entry for thread {thread_id} which is {os.stat(file_path := os.path.join(path, file)).st_size / 1024:.2f} Kb large. Moving it to {target}...')
                move(file_path, os.path.join(target, file))


@main.command()
@option('--port', '-p', type = int, default = 1719)
@option('--host', '-h', type = str, default = '0.0.0.0')
@option('--timeout', '-t', type = int, default = 60)
@option('--protocol', '-r', type = Choice(('http', 'https'), case_sensitive = True), default = 'http')
def start_proxy(host: str, port: int, timeout: int, protocol: str):
    app = Flask(__name__)

    _ARHIVACH_THREAD_URL = f'{protocol}://arhivach.top/thread/{{thread}}'
    _ARHIVACH_INDEX_URL = f'{protocol}://arhivach.top/index/{{offset}}'

    @app.get('/thread/<thread>')
    def get_thread(thread: int):
        response = get(_ARHIVACH_THREAD_URL.format(thread = thread), timeout = timeout)

        return response.content, response.status_code

    @app.get('/index/<offset>')
    def get_index(offset: int):
        _url = _ARHIVACH_INDEX_URL.format(offset = offset)
        print(f'Pulling url {_url}')
        response = get(_url, timeout = timeout)

        return response.content, response.status_code

    app.run(host = host, port = port)

    print(f'Starting proxy at {host}:{port}')


@main.command()
@option('--index', '-i', type = str, default = 'index.tsv')
@option('--threads', '-t', type = str, default = 'threads')
@option('--keywords', '-k', type = str, default = 'creepy-dict.txt')
@option('--min-length', '-s', type = int, default = 1000)
@option('--max-length', '-x', type = int, default = 4000)
@option('--output-path', '-o', type = str, default = 'stories.txt')
@option('--trace', '-r', is_flag = True)
def collect_creepy_stories(index: str, threads: str, keywords: str, min_length: int, max_length: int, output_path: str, trace: bool):
    content = read_csv(index, sep = '\t').dropna()

    with open(keywords, 'r', encoding = 'utf-8') as file:
        keywords = file.read().split('\n')

    keywords = keywords[:-1]
    stories = None if trace else []

    for index, row in content[content['title'].str.contains('|'.join(keywords), case = False)].iterrows():
        if trace:
            print(row['title'])
            continue

        thread = row['thread']
        folder = row['folder']

        path = os.path.join(threads, folder, f'{thread:08d}.txt')

        with open(path, 'r', encoding = 'utf-8') as file:
            lines = file.readlines()

        for line in lines:
            if min_length < len(line) < max_length:
                stories.append(line)

    if not trace:
        with open(output_path, 'w', encoding = 'utf-8') as file:
            file.writelines(stories)


if __name__ == '__main__':
    main()
