"""Apply the G06 color and fallback oracle to the four Android thumbnail captures."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def check(directory):
    names = ('amber', 'blue', 'blue-after-fallback', 'blue-low-light')
    paths = {name: directory / f'{name}.png' for name in names}
    images = {}
    for name, path in paths.items():
        with Image.open(path) as image:
            images[name] = image.convert('RGB')
    width, height = images['blue'].size
    if {image.size for image in images.values()} != {(width, height)} or width != 192 or height < 30:
        raise ValueError('expected matching 192-pixel-wide thumbnails')

    # The fixed camera aims at the origin. Compare a center region to keep
    # temporal variation or a matching clear color outside the object from
    # dominating the fallback check.
    bounds = (width * 3 // 8, height // 5, width * 5 // 8, height * 4 // 5)
    model_region = {name: image.crop(bounds) for name, image in images.items()}

    def difference(left, right):
        delta = ImageChops.difference(model_region[left], model_region[right])
        return {'mean_channel_error': sum(ImageStat.Stat(delta).mean) / 3,
                'max_channel_error': max(high for _, high in delta.getextrema())}

    def model_color(name, axis, other):
        background = images[name].getpixel((0, 0))
        return sum(pixel[axis] > background[axis] + 6 and pixel[axis] > pixel[other] * 1.3
                   for pixel in model_region[name].get_flattened_data())

    amber = model_color('amber', 0, 2)
    blue = model_color('blue', 2, 0)
    pairs = {'asset_switch': difference('amber', 'blue'),
             'unsupported_extension_retains_blue': difference('blue', 'blue-after-fallback'),
             'lighting_switch': difference('blue-after-fallback', 'blue-low-light')}
    passed = (amber > 100 and blue > 100 and pairs['asset_switch']['mean_channel_error'] > 5
              and pairs['unsupported_extension_retains_blue']['max_channel_error'] <= 3
              and pairs['lighting_switch']['mean_channel_error'] > 3)
    return {'status': 'PASS' if passed else 'FAIL', 'model_region': bounds,
            'warm_model_pixels': amber, 'blue_model_pixels': blue, 'pairs': pairs,
            'images_sha256': {name: sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    report = check(args.directory)
    print(json.dumps(report, indent=2))
    return report['status'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
