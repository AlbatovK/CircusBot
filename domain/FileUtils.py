import json
from os import path

config_name, assets_dir = 'config.json', "assets"


def get_assets_path(filename: str) -> str:
    return path.dirname(__file__)[:-6:] + assets_dir + "\\" + filename


def get_config() -> str:
    src = get_assets_path(config_name)
    with open(src, 'r') as config_file:
        return parse_from_file(config_file)


def parse_from_file(read_file) -> str:
    return json.load(read_file)
