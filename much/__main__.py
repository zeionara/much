from click import group, argument

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


if __name__ == '__main__':
    main()
