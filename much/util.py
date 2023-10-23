import re

SPACE_TEMPLATE = re.compile('\s+')
SPACE = ' '


def normalize(string: str):
    return SPACE_TEMPLATE.sub(SPACE, string).strip()
