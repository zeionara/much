import re

SPACE_TEMPLATE = re.compile('\s+')
PURE_SPACES_TEMPLATE = re.compile('\s*')
SPACE = ' '


def normalize(string: str):
    return SPACE_TEMPLATE.sub(SPACE, string).strip()

def pure_spaces(string: str):
    return PURE_SPACES_TEMPLATE.fullmatch(string) is not None
