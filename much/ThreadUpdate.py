from dataclasses import dataclass


@dataclass
class ThreadUpdate:
    i: int
    board: str = None
    updated: bool = True
