from PIL import Image
from dateutil import parser as date_parser


def load_image(path: str) -> Image.Image:
    return Image.open(path)


def parse_timestamp(s: str):
    return date_parser.parse(s)
