from dataclasses import dataclass
from datetime import datetime


TIMESTAMP_FORMAT = '%d-%m-%Y'


@dataclass
class IndexEntry:
    thread_id: int
    timestamp: datetime
    title: str
    folder: str = None
    is_open: str = False

    @classmethod
    def from_json(cls, json: dict):
        date_as_string = json.get('date')

        return cls(
            thread_id = json.get('thread'),
            timestamp = None if date_as_string is None else datetime.strptime(date_as_string, TIMESTAMP_FORMAT),
            title = json.get('title'),
            folder = json.get('folder'),
            is_open = json.get('open', False)
        )

    def as_record(self):
        return {
            'thread': self.thread_id,
            'date': self.timestamp.strftime(TIMESTAMP_FORMAT),
            'title': self.title,
            'folder': self.folder,
            'open': self.is_open
        }
