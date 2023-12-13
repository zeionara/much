import re

SPACE_TEMPLATE = re.compile('\s+')
PURE_SPACES_TEMPLATE = re.compile('\s*')
SPACE = ' '


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
