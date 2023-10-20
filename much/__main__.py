import os
from pathlib import Path
from shutil import copyfile

from click import group, argument, option
from requests import get
from bs4 import BeautifulSoup
from pandas import DataFrame, read_csv, concat
from tqdm import tqdm

from .Fetcher import Fetcher
from .Exporter import Exporter, Format


@group()
def main():
    pass


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

PATH = '../batch/batch'
INDEX = '../batch/index.tsv'


@main.command()
@argument('page', type = int)
@option('--path', '-p', type = str, help = 'path to the directory which will contain pulled files', default = PATH)
@option('--index', '-i', type = str, help = 'path to the file with pulled files index', default = INDEX)
def fetch(page: int, path: str, index: str):
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
        link = thread.find_previous("a")
        # records.append({'thread': int(thread.text[2:-2]), 'date': f'{ROOT}{link["href"]}', 'title': link.text})
        records.append({
            'thread': (thread_id := int(thread.text[2:-2])),
            'date': '-'.join(link["href"].split('/')[3].split('-')[::-1]),
            'title': link.text
        })

        file = os.path.join(path, f'{thread_id}.txt')

        exporter.export(fetcher.fetch(url = f'{ROOT}{link["href"]}'), Format.TXT, path = file)

        i += 1

    # print(f'Pulled {i} threads')
    # print(records[:5])

    df = DataFrame.from_records(records)

    if os.path.isfile(index):
        df = concat([read_csv(index, sep = '\t'), df])

    df.to_csv(index, sep = '\t', index = False)


@main.command()
@argument('n', type = int, default = 10)
@option('--path', '-p', type = str, help = 'path to the directory which will contain pulled files', default = PATH)
@option('--index', '-i', type = str, help = 'path to the file with pulled files index', default = INDEX)
def top(n: int, path: str, index: str):
    index = read_csv(index, sep = '\t')

    for file in sorted(
        [
            file
            for file in [
                os.path.join(path, file)
                for file in os.listdir(path)
            ]
            if os.path.isfile(file)
        ],
        key = lambda file: os.stat(file).st_size,
        reverse = True
    )[:n]:
        thread_id = int(Path(file).stem)

        print(f'{os.stat(file).st_size / 1024:.2f} KB', thread_id, index.loc[index.thread == thread_id].iloc[0]['title'])


@main.command()
@argument('thread-id', type = int)
@argument('name', type = str)
@option('--source-path', '-s', type = str, help = 'path to the directory which will contain pulled files', default = PATH)
@option('--destination-path', '-d', type = str, help = 'path where the chosen file will be copied with given name', default = 'assets/starred')
def star(thread_id: int, name: str, source_path: str, destination_path: str):
    if not os.path.isdir(destination_path):
        os.mkdir(destination_path)

    copyfile(os.path.join(source_path, f'{thread_id}.txt'), os.path.join(destination_path, f'{name}.txt'))


if __name__ == '__main__':
    main()
