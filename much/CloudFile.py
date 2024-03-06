from datetime import datetime


DATE_TIME_FORMAT = '%d-%m-%Y %H:%M:%S'


class CloudFile:
    def __init__(self, name: str, timestamp: datetime):
        self.name = name
        self.timestamp = timestamp

    @classmethod
    def from_json(cls, json: dict):
        return cls(json['name'], datetime.fromtimestamp(json['mtime']))

    def __repr__(self):
        return f'{self.name} {self.timestamp.strftime(DATE_TIME_FORMAT)}'
