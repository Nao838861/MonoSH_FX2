"""Exhaustively check the CPU color sampler's two-product axis recurrence.

Every source dimension in the shipped assets, destination size 1..255, and
integer origin intersecting a 256-pixel screen is covered. This also covers
the vertical sampler's smaller 192-pixel screen. Reflection is applied after
sampling and therefore preserves equality of the verified Q8.8 coordinates.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'game/v001/assets'


def verify():
    dimensions = set()
    for asset in range(44):
        with Image.open(ASSETS / f'{asset:02d}.png') as image:
            dimensions.update(image.size)

    checked = 0
    for size in range(1, 256):
        origin = np.arange(1 - size, 256, dtype=np.int64)
        first_tile = np.maximum(origin, 0) // 8
        last_tile = (np.minimum(origin + size, 256) - 1) // 8
        tile_count = last_tile - first_tile + 1
        first_distance = first_tile * 8 + 4 - origin

        for source_size in sorted(dimensions):
            step = source_size * 256 // size
            # Hardware divide provides both quotient and remainder.
            maximum = source_size * 256 - (source_size * 256) % size - step
            coordinate = np.minimum(np.maximum(first_distance, 0), size - 1) * step
            first_step = np.where(
                first_distance < 0,
                np.minimum(size - 1, first_distance + 8) * step,
                step * 8,
            )
            for tile in range(int(tile_count.max())):
                active = tile < tile_count
                actual = np.minimum(coordinate, maximum)
                expected = np.minimum(size - 1, np.maximum(0, first_distance + tile * 8)) * step
                mismatch = active & (actual != expected)
                if np.any(mismatch):
                    index = int(np.flatnonzero(mismatch)[0])
                    raise AssertionError({
                        'sourceSize': source_size,
                        'destinationSize': size,
                        'origin': int(origin[index]),
                        'tileOffset': tile,
                        'actual': int(actual[index]),
                        'expected': int(expected[index]),
                    })
                checked += int(active.sum())
                # Reproduce the 65816's unsigned 16-bit addition, including
                # tiny sprites where a large step could otherwise wrap.
                coordinate = (coordinate + (first_step if tile == 0 else step * 8)) & 65535

    result = {
        'sourceDimensions': len(dimensions),
        'destinationSizes': 255,
        'sampleCoordinatesChecked': checked,
        'mismatches': 0,
    }
    print('CPU color coordinate recurrence:', result)
    return result


if __name__ == '__main__':
    verify()
