from enum import Enum
from json import dump
from typing import Iterable

from .Fetcher import Topic


class Format(Enum):
    JSON = 'json'
    TXT = 'txt'


class Exporter:
    def __init__(self):
        pass

    def export(self, topics: Iterable[Topic], format: Format = Format.JSON, path = 'assets/topics.json'):
        if format == Format.JSON:
            data = {
                'topics': [
                    {
                        'title': topic.title,
                        'comments': topic.comments
                    }
                    for topic in topics
                ]
            }

            with open(path, 'w', encoding = 'utf-8') as file:
                dump(data, file, ensure_ascii = False, indent = 4)
        elif format == Format.TXT:
            lines = []

            for topic in topics:
                lines.append(topic.title)
                for comment in topic.comments:
                    lines.append(comment)
                lines.append('')

            with open(path, 'w', encoding = 'utf-8') as file:
                file.write('\n'.join(lines))
        else:
            raise ValueError(f'Unknown format: {format}')
