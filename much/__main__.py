import re
import os
from pathlib import Path
from shutil import copyfile, move
from html import unescape
from multiprocessing import Pool
from datetime import datetime, timedelta
from math import ceil
from time import sleep

from click import group, argument, option
from requests import get
from bs4 import BeautifulSoup
from pandas import DataFrame, read_csv, concat
from tqdm import tqdm
from requests.exceptions import ConnectionError, ChunkedEncodingError
from flask import Flask

from .Fetcher import Fetcher, Topic, SSL_ERROR_DELAY
from .Exporter import Exporter, Format
from .Post import Post
from .util import normalize, SPACE


@group()
def main():
    pass


THREAD_URL = 'https://2ch.hk/b/res/{thread}.html'
ARHIVACH_THREAD_URL = '{protocol}://arhivach.top/thread/{thread}'
ARHIVACH_CACHE_PATH = 'assets/cache.html'

BOARD_NAME_TEMLATE = re.compile('/[a-zA-Z0-9]+/')


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
        print(f'Can\'t decode date: {date}')
        return date


TIMEOUT = 3600


@main.command()
@option('--source', '-s', default = 'assets/index.tsv')
@option('--destination', '-d', default = 'assets/index.tsv')
def sort(source: str, destination: str):
    read_csv(source, sep = '\t').sort_values(by = ['thread']).to_csv(destination, sep = '\t', index = False)


@main.command()
@argument('url', type = str, default = 'http://arhivach.top/index/{offset}/')
@option('--start', '-s', type = int, default = 935475)
@option('--debug', '-d', is_flag = True)
@option('--n-top', '-n', type = int, default = None)
@option('--index', '-i', type = str, default = None)
@option('--step', '-t', type = int, default = 25)
def filter(url: str, start: int, debug: bool, n_top: int, index: str, step: int):
    records = []

    if index is None:
        content = None
        seen_keys = set()
    else:
        content = read_csv(index, sep = '\t')
        seen_keys = set(content.thread)

        if len(seen_keys) != content.shape[0]:
            raise ValueError(f'Input index contains duplicates ({len(seen_keys)} != {content.shape[0]})')

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
                    response = get(url.format(offset = offset), timeout = TIMEOUT)
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
@option('--path', '-p', type = str, default = 'threads')
@option('--index', '-i', type = str, default = 'index.tsv')
@option('--batch-size', '-b', help = 'how many threads to put in a folder', default = 10000)
def load(url: str, path: str, index: str, batch_size: int):
    last_records_list = read_csv(index, sep = '\t').to_dict(orient = 'records') if os.path.isfile(index) else None
    last_records = None if last_records_list is None else {
        item['thread']: item
        for item in last_records_list
    }

    if not os.path.exists(path):
        os.makedirs(path)

    response = get(url)

    if (code := response.status_code) != 200:
        raise ValueError(f'Inacceptable status code: {code}')

    json = response.json()
    records_list = []
    records = {}

    offset = 0
    batch_max_count = offset + batch_size - 1

    while True:
        batch_folder_name = BATCH_FOLDER_NAME.format(first = offset, last = batch_max_count)
        batch_folder_path = os.path.join(path, batch_folder_name)
        batch_folder_size = None

        if not os.path.isdir(batch_folder_path):
            os.makedirs(batch_folder_path)
            batch_folder_size = 0
        else:
            batch_folder_size = len([name for name in os.listdir(batch_folder_path)])

            if batch_folder_size < batch_size:
                break
            else:
                offset = batch_max_count + 1
                batch_max_count = offset + batch_size - 1

    fetcher = Fetcher()
    exporter = Exporter()

    for thread in tqdm(json['threads']):
        day, month, year = thread['date'].split(' ')[0].split('/')

        thread_id = thread['num']

        last_thread_path = None
        last_batch_folder_name = None
        if last_records is not None and (last_record := last_records.get(thread_id)) is not None:
            last_thread_path = os.path.join(path, last_record['folder'], f'{thread_id}.txt')
            last_batch_folder_name = last_record['folder']

        if last_thread_path is None and batch_folder_size >= batch_size:
            offset = batch_max_count + 1
            batch_max_count = offset + batch_size - 1
            batch_folder_name = BATCH_FOLDER_NAME.format(first = offset, last = batch_max_count)
            batch_folder_path = os.path.join(path, batch_folder_name)

            if os.path.isdir(batch_folder_path):
                raise ValueError(f'Folder {batch_folder_path} already exists')

            os.makedirs(batch_folder_path)
            batch_folder_size = 0

        # print(thread_id, last_thread_path, last_batch_folder_name)

        records_list.append(
            record := {
                'thread': thread_id,
                'date': f'{day}-{month}-20{year}',
                # 'path': path.replace('../', ''),
                'title': Post.from_body(BeautifulSoup(thread['comment'], 'html.parser'))[1].text,
                'folder': batch_folder_name if last_batch_folder_name is None else last_batch_folder_name,
                'open': True
            }
        )

        # try:
        exporter.export(
            fetcher.fetch(THREAD_URL.format(thread = thread_id)),
            format = Format.TXT,
            path = os.path.join(batch_folder_path, f'{thread_id}.txt') if last_thread_path is None else last_thread_path
        )
        records[thread_id] = record
        if last_thread_path is None:
            batch_folder_size += 1
        # except TypeError:
        #     print(f'Cant process url {thread_url}. Skipping...')

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

PATH = 'threads'
INDEX = 'index.tsv'


def expand_title(title: str, topics: [Topic]):
    title = unescape(title)

    for topic in topics:
        match = topic.find(title)

        if match is not None:
            return match

    return title


BATCH_FOLDER_NAME = '{first:08d}-{last:08d}'


def grab_one(i: int, row: dict, batch_size: int, path: str, skip_empty: bool, protocol: str):
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

    if os.path.isfile(thread_path) and (skip_empty or os.stat(thread_path).st_size > 0):
        # print(f'File {thread_path} exists. Not pulling')
        # pbar.update()
        return
        # continue

    fetched = False

    while not fetched:
        try:
            exporter.export(fetcher.fetch(url = url, verbose = False), Format.TXT, path = thread_path)
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
def grab(path: str, index: str, batch_size: int, verbose: bool, pretend: bool, n_workers: int, skip_empty: bool, protocol: str):
    if not os.path.isdir(path):
        os.makedirs(path)

    df = read_csv(index, sep = '\t')

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
        pool.starmap(grab_one, [(i, row, batch_size, path, skip_empty, protocol) for i, row in df.iterrows()])


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

    for path, _, files in os.walk(path):
        for file in files:
            folder = Path(path).stem
            thread_id = int(Path(file).stem)

            row = index.loc[(index.thread == thread_id) & (index.folder == folder)]

            size = row.shape[0]

            if size > 1:
                raise ValueError(f'There are multiple threads with id {thread_id} in folder {folder}')
            if size < 1:
                print(f'Missing index entry for thread {thread_id} which is {os.stat(file_path := os.path.join(path, file)).st_size / 1024:.2f} Kb large. Moving it to {target}...')
                move(file_path, os.path.join(target, file))


@main.command()
@option('--port', '-p', type = int, default = 1719)
@option('--host', '-h', type = str, default = '0.0.0.0')
@option('--timeout', '-t', type = int, default = 60)
def start_proxy(host: str, port: int, timeout: int):
    app = Flask(__name__)

    @app.get('/thread/<thread>')
    def get_thread(thread: int):
        response = get(ARHIVACH_THREAD_URL.format(thread = thread), timeout = timeout)

        return response.content, response.status_code

    app.run(host = host, port = port)

    print(f'Starting proxy at {host}:{port}')


if __name__ == '__main__':
    main()
