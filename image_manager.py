from io import BytesIO
import os
import requests
import shared
from urllib.parse import urlparse, urlunparse

from PIL import Image


def get_filename_from_url(image_url):
    url_parts = urlparse(image_url, scheme='http', allow_fragments=True)
    image_path = url_parts.path
    split_path = os.path.split(image_path)
    result = os.path.join(shared.CONFIG['constant']['image_dir'], split_path[-1])
    return result


def save_image(image_url, filename):
    image_data = requests.get(urlunparse(urlparse(image_url, scheme='http', allow_fragments=True))).content
    if image_data:
        try:
            img = Image.open(BytesIO(image_data))
            img.thumbnail((400, 300))
            img.save(filename)
        except:
            with open(filename, 'wb') as file:
                file.write(b'')


def cache_image(image_url):
    filename = get_filename_from_url(image_url)
    if not os.path.exists(filename):
        save_image(image_url, filename)
    return filename


def load_image(image_url):
    filename = cache_image(image_url)
    with open(filename, 'rb') as file:
        return filename, file.read()


def test():
    assert (get_filename_from_url('https://assets.utahrealestate.com/photos/640x480/0e81e16b_3dc1_47b5_bfb4_6e5504ba573e.jpg') == os.path.join(shared.CONFIG['constant']['image_dir'], '0e81e16b_3dc1_47b5_bfb4_6e5504ba573e.jpg'))
    assert(get_filename_from_url('https://assets.utahrealestate.com/photos/640x480/nophoto.jpg') == os.path.join(shared.CONFIG['constant']['image_dir'], 'nophoto.jpg'))
    assert (get_filename_from_url(
        'https://img.ksl.com/mx/mplace-homes.ksl.com/b27faa11-9134-4220-b2c3-2f59854f7fc6.jpg?filter=marketplace/400x300') == os.path.join(shared.CONFIG['constant']['image_dir'], 'b27faa11-9134-4220-b2c3-2f59854f7fc6.jpg'))


if __name__ == '__main__':
    test()
