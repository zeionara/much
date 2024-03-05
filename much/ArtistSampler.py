from random import choice


class ArtistSampler:
    def __init__(self, path: str = 'artists.txt'):
        with open(path, 'r', encoding = 'utf-8') as file:
            self.artists = [line[:-1] for line in file.readlines() if len(line) > 1]

    def sample(self):
        return choice(self.artists)
